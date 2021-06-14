import inquirer
import value_functions
from mf import ICFPMF
from util import DatasetFormatter
import numpy as np
dsf = DatasetFormatter()
dsf = dsf.load()
# dsf.get_base()

mf = ICFPMF()
mf.load_var(dsf.matrix_users_ratings[dsf.train_uids])
mf = mf.load()

itr = value_functions.LinearUCB.getInstance(
    var=mf.var,
    user_lambda=mf.user_lambda,
    consumption_matrix=dsf.matrix_users_ratings,
)
for alpha in np.linspace(0, 1, 6):
    itr.alpha = alpha
    itr.interact(dsf.test_uids, mf.items_means)
