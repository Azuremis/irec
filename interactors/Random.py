import numpy as np
from tqdm import tqdm
from .Interactor import Interactor
import random
class Random(Interactor):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

    def interact(self, uids):
        super().interact()
        num_users = len(uids)
        for idx_uid in tqdm(range(num_users)):
            uid = uids[idx_uid]
            iids= list(range(self.consumption_matrix.shape[1]))
            random.shuffle(iids)
            self.result[uid].extend(iids[:self.interactions])
        self.save_result()
        
