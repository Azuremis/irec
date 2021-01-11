from os.path import dirname, realpath, sep, pardir
import sys, os
sys.path.append(dirname(realpath(__file__)) + sep + pardir)

import numpy as np
import scipy.sparse

from utils.Parameterizable import Parameterizable
from collections import defaultdict
import pickle
import json
from .Interactor import Interactor

class ExperimentalInteractor(Interactor,Parameterizable):
    def __init__(self,*args, **kwargs):
        Interactor.__init__(self,*args, **kwargs)
        Parameterizable.__init__(self)
    def train(self,train_data):
        super().train(train_data)
        # self.t = 0
    # def increment_time(self):
    #     self.t += 1
