from .ICF import ICF
import numpy as np
from tqdm import tqdm
import util
from threadpoolctl import threadpool_limits
import ctypes
from numba import jit


@jit(nopython=True)
def _central_limit_theorem(k):
    p = len(k)
    x = (np.sum(k) - p/2)/(np.sqrt(p/12))
    return x

@jit(nopython=True)
def _numba_multivariate_normal(mean,cov):
    n = len(mean)
    cov_eig = np.linalg.eig(cov)
    x = np.zeros(n)
    for i in range(n):
        x[i] = _central_limit_theorem(np.random.uniform(0,1,20000)) # best parameter is 20000 in terms of speed and accuracy in distribution sampling
    return ((np.diag(cov_eig[0])**(0.5)) @ cov_eig[1].T @ x)+mean

@jit(nopython=True)
def _sample_items_weights(user_candidate_items, items_means, items_covs):
    n= len(user_candidate_items)
    num_lat = items_means.shape[1]
    qs = np.zeros((n,num_lat))
    for i, item in enumerate(user_candidate_items):
        item_mean = items_means[item]
        item_cov = items_covs[item]
        qs[i] = _numba_multivariate_normal(item_mean,item_cov)
    return qs

class LinearThompsonSampling(ICF):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

    def interact(self, items_means,items_covs):
        super().interact()
        uids = self.test_users
        self.items_means = items_means
        self.items_covs = items_covs
        num_users = len(uids)
        # get number of latent factors 

        self_id = id(self)
        with threadpool_limits(limits=1, user_api='blas'):
            args = [(self_id,int(uid),) for uid in uids]
            results = util.run_parallel(self.interact_user,args)
        for i, user_result in enumerate(results):
            self.results[uids[i]] = user_result
        self.save_results()


    @staticmethod
    def interact_user(obj_id, uid):
        self = ctypes.cast(obj_id, ctypes.py_object).value
        if not issubclass(self.__class__,ICF): # DANGER CODE
            raise RuntimeError

        num_lat = len(self.items_means[0])
        I = np.eye(num_lat)

        user_candidate_items = np.array(list(range(len(self.items_means))))
        # get number of latent factors 
        b = np.zeros(num_lat)
        A = self.user_lambda*I
        result = []

        num_correct_items = 0
        for i in range(self.interactions):
            tmp_max_qs = dict()
            mean = np.dot(np.linalg.inv(A),b)
            cov = np.linalg.inv(A)*self.var
            p = np.random.multivariate_normal(mean,cov)
            qs = _sample_items_weights(user_candidate_items,self.items_means, self.items_covs)

            items_score = p @ qs
            best_items = user_candidate_items[np.argsort(items_score)[::-1]][:self.interaction_size]

            user_candidate_items = user_candidate_items[~np.isin(user_candidate_items,best_items)]
            result.extend(best_items)
            
            for item in result[i*self.interaction_size:(i+1)*self.interaction_size]:
                max_q = qs[item == user_candidate_items]
                A += max_q[:,None].dot(max_q[None,:])
                if self.get_reward(uid,max_i) >= self.threshold:
                    b += self.get_reward(uid,max_i)*max_q
                    num_correct_items += 1
                    if self.exit_when_consumed_all and num_correct_items == self.users_num_correct_items[uid]:
                        print(f"Exiting user {uid} with {len(result)} items in total and {num_correct_items} correct ones")
                        return np.array(result)

                    
        return result
