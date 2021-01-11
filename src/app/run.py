from os.path import dirname, realpath, sep, pardir
import os
import sys
sys.path.append(dirname(realpath(__file__)) + sep + pardir + sep + "lib")

import inquirer
import interactors
import mf
from lib.InteractorsRunner import InteractorsRunner
from sklearn.decomposition import NMF
import numpy as np
import scipy.sparse
from lib.DatasetManager import DatasetManager
import yaml

dm = DatasetManager()
# dm.request_dataset_preprocessor()
# dm.initialize_engines()
# dm.load()


            
interactors_preprocessor_paramaters = yaml.load(open("settings"+sep+"interactors_preprocessor_parameters.yaml"),Loader=yaml.SafeLoader)
print(interactors_preprocessor_paramaters)
interactors_names = yaml.load(open("settings"+sep+"interactors_names.yaml"),Loader=yaml.SafeLoader)
print(interactors_names)


ir = InteractorsRunner(dm,interactors_names,interactors_preprocessor_paramaters)
print(ir.select_interactors())

# ir = InteractorsRunner(dm)
# ir.select_interactors()
# ir.run_interactors()
# ir.run_bases(['tr_te_yahoo_music',
#               'tr_te_good_books','tr_te_ml_10m'])
