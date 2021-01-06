import numpy as np
from tqdm import tqdm
from .ExperimentalInteractor import ExperimentalInteractor
import random
class Random(ExperimentalInteractor):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

    def interact(self):
        super().interact()
        uids = self.test_users
        num_users = len(uids)
        for idx_uid in tqdm(range(num_users)):
            uid = uids[idx_uid]
            iids= list(range(self.train_consumption_matrix.shape[1]))
            random.shuffle(iids)
            self.results[uid].extend(iids[:self.interactions*self.interaction_size])
        self.save_results()
        
