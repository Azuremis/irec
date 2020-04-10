from .ICF import ICF
import numpy as np
import random
from tqdm import tqdm
import util
from threadpoolctl import threadpool_limits

class LinearEGreedy(ICF):
    def __init__(self, epsilon=0.05, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epsilon = epsilon

    def interact(self, uids, items_means):
        super().interact()
        self.items_means = items_means
        num_users = len(uids)
        # get number of latent factors 
        num_lat = len(items_means[0])
        I = np.eye(num_lat)
        with threadpool_limits(limits=1, user_api='blas'):
            args = [(int(uid),) for uid in uids]
            result = util.run_parallel(self.interact_user,args)

        for i, user_result in enumerate(result):
            self.result[uids[i]] = user_result
        self.save_result()

    @classmethod
    def interact_user(cls,uid):
        self = cls.getInstance()
        num_lat = len(self.items_means[0])
        I = np.eye(num_lat)
        # uid = uids[idx_uid]
        result = []
        user_candidate_items = list(range(len(self.items_means)))
        b = np.zeros(num_lat)
        A = self.user_lambda*I
        REC_ONE = False
        # if uid == 379:
        #     print(uid)
        for i in range(self.interactions):
            for j in range(self.interaction_size):
                mean = np.dot(np.linalg.inv(A),b)
                max_i = np.NAN
                max_item_mean = np.NAN
                max_e_reward = np.NINF
                if not REC_ONE:
                    max_i = random.choice(user_candidate_items)
                    max_item_mean = self.items_means[max_i]
                    max_e_reward = np.NAN
                else:
                    if self.epsilon < np.random.rand():
                        for item in user_candidate_items:
                            item_mean = self.items_means[item]
                            # q = np.random.multivariate_normal(item_mean,item_cov)
                            e_reward = mean.T @ item_mean

                            if e_reward > max_e_reward:
                                max_i = item
                                max_item_mean = item_mean
                                max_e_reward = e_reward
                    else:
                        max_i = random.choice(user_candidate_items)
                        max_item_mean = self.items_means[max_i]
                user_candidate_items.remove(max_i)

                # if uid == 379:
                #     print("recommended item", max_i, "reward", self.get_reward(uid,max_i), "expected reward", max_e_reward)
                #     print(result)
                result.append(max_i)
            # for max_i in result[i*self.interaction_size:(i+1)*self.interaction_size]:
                if self.get_reward(uid,max_i) >= self.values[-2]:
                    max_item_mean = self.items_means[max_i]
                    A += max_item_mean[:,None].dot(max_item_mean[None,:])
                    b += self.get_reward(uid,max_i)*max_item_mean
                    REC_ONE = True


        return result
