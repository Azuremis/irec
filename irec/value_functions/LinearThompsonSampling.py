from .ICF import ICF
import numpy as np
from tqdm import tqdm
from threadpoolctl import threadpool_limits
import ctypes
from numba import jit
import scipy
import mf
import joblib


@jit(nopython=True)
def _central_limit_theorem(k):
    p = len(k)
    x = (np.sum(k) - p / 2) / (np.sqrt(p / 12))
    return x


@jit(nopython=True)
def _numba_multivariate_normal(mean, cov):
    n = len(mean)
    cov_eig = np.linalg.eigh(cov)  # suppose that the matrix is symmetric
    x = np.zeros(n)
    for i in range(n):
        x[i] = _central_limit_theorem(
            np.random.uniform(0, 1, 200)
        )  # best parameter is 20000 in terms of speed and accuracy in distribution sampling
    return ((np.diag(cov_eig[0])**(0.5)) @ cov_eig[1].T @ x) + mean


@jit(nopython=True)
def _sample_items_weights(user_candidate_items, items_means, items_covs):
    n = len(user_candidate_items)
    num_lat = items_means.shape[1]
    qs = np.zeros((n, num_lat))
    for i, item in enumerate(user_candidate_items):
        item_mean = items_means[item]
        item_cov = items_covs[item]
        qs[i] = _numba_multivariate_normal(item_mean, item_cov)
    return qs


class LinearThompsonSampling(ICF):
    """Linear Thompson Sampling.
    An adaptation of the original Thompson Sampling to measure the latent dimensions by a PMF formulation [1]_.

    References
    ----------
    .. [1] Abeille, Marc, and Alessandro Lazaric. "Linear thompson sampling revisited." 
       Artificial Intelligence and Statistics. PMLR, 2017.
    """
    def __init__(self, *args, **kwargs):
        """__init__.

        Args:
            args:
            kwargs:
        """
        super().__init__(*args, **kwargs)

    def reset(self, observation):
        """reset.

        Args:
            observation: 
        """ 
        train_dataset = observation
        super().reset(train_dataset)
        self.train_dataset = train_dataset
        self.train_consumption_matrix = scipy.sparse.csr_matrix(
            (self.train_dataset.data[:, 2],
             (self.train_dataset.data[:, 0], self.train_dataset.data[:, 1])),
            (self.train_dataset.num_total_users,
             self.train_dataset.num_total_items))
        self.num_total_items = self.train_dataset.num_total_items

        mf_model = mf.ICFPMFS(self.iterations,
                              self.var,
                              self.user_var,
                              self.item_var,
                              self.stop_criteria,
                              num_lat=self.num_lat)
        mf_model_id = joblib.hash(
            (mf_model.get_id(), self.train_consumption_matrix))

        if pdm.file_exists(mf_model_id):
            mf_model = pdm.load(mf_model_id)
        else:
            mf_model.fit(self.train_consumption_matrix)
            pdm.save(mf_model_id, mf_model)

        self.items_means = mf_model.items_means
        self.items_covs = mf_model.items_covs
        self.num_latent_factors = len(self.items_latent_factors[0])

        self.I = np.eye(self.num_latent_factors)

        bs = defaultdict(lambda: np.zeros(self.num_latent_factors))
        As = defaultdict(lambda: self.get_user_lambda() * I)

    def action_estimates(self, candidate_actions):
        """action_estimates.

        Args:
            candidate_actions: (user id, candidate_items)
        
        Returns:
            numpy.ndarray:
        """
        uid = candidate_actions[0]
        candidate_items = candidate_actions[1]
        b = bs[uid]
        A = As[uid]

        mean = np.dot(np.linalg.inv(A), b)
        cov = np.linalg.inv(A) * self.var
        p = np.random.multivariate_normal(mean, cov)
        qs = _sample_items_weights(candidate_items, self.items_means,
                                   self.items_covs)

        items_score = p @ qs.T
        return items_score, {'qs': qs, 'candidate_items': candidate_items}

    def update(self, observation, action, reward, info):
        """update.

        Args:
            observation:
            action: (user id, item)
            reward (float): reward
            info: 
        """
        uid = action[0]
        item = action[1]
        additional_data = info
        max_q = additional_data['qs'][np.argmax(
            item == additional_data['candidate_items']), :]
        A += max_q[:, None].dot(max_q[None, :])
        b += reward * max_q
