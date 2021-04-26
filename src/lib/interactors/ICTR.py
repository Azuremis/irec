from threadpoolctl import threadpool_limits
import copy
import numpy as np
from tqdm import tqdm
from .ExperimentalInteractor import ExperimentalInteractor
import matplotlib.pyplot as plt
import os
import scipy.sparse
import scipy.stats
from collections import defaultdict
import random
from .MFInteractor import MFInteractor
from tqdm import tqdm
from numba import njit, jit
import mf
from utils.PersistentDataManager import PersistentDataManager
import joblib

@njit
def _softmax(x):
    return np.exp(x - np.max(x)) / np.sum(np.exp(x - np.max(x)))

class _Particle:
    def __init__(self,num_users,num_items,num_lat):
        self.alpha = 1
        self.beta = 1
        self.lambda_ = np.ones(shape=(num_users,num_lat))
        self.eta = np.ones(shape=(num_lat,num_items))
        self.mu = np.ones(shape=(num_items,num_lat))
        # self.Sigma = np.zeros(shape=(num_items,num_lat,num_lat))
        self.Sigma = np.array([np.identity(num_lat) for _ in range(num_items)])
        self.sigma_n_2 = 1
        self.p = np.zeros(shape=(num_users,num_lat))
        self.q = np.zeros(shape=(num_items,num_lat))
        self.Phi = np.zeros(shape=(num_lat,num_items))
    # def p_expectations(self,uid,topic=None,reward=None):
    def p_expectations(self,uid,reward=None):
        computed_sum = np.sum(self.lambda_[uid])
        user_lambda = np.copy(self.lambda_[uid])
        if reward!=None:
            # user_lambda[topic] += reward
            user_lambda += reward
            computed_sum += reward
        return user_lambda/computed_sum
    def Phi_expectations(self,item,reward=None):
        computed_sum = np.sum(self.eta,axis=1)
        item_eta =self.eta[:,item]
        if reward!=None:
            item_eta += reward
            computed_sum += reward
        return item_eta/computed_sum
    def particle_weight(self,uid,item,reward):
        # print(self.p[uid],self.q[item])
        norm_val = scipy.stats.norm(self.p[uid]@self.q[item],self.sigma_n_2).pdf(reward)
        return np.sum(norm_val+self.p_expectations(uid) * self.Phi_expectations(item))
    def compute_theta(self,uid,item,reward):
        return self.p_expectations(uid,reward=reward)*self.Phi_expectations(item,reward=reward)
    def select_z_topic(self,uid,item,reward):
        theta = self.compute_theta(uid,item,reward)
        theta = _softmax(theta)
        # print(np.random.multinomial(1,theta))
        topic = np.argmax(np.random.multinomial(1,theta))
        # print()
        # print(topic,theta)
        return topic
    def update_parameters(self,uid,item,reward,topic):
        new_Sigma = np.linalg.inv(np.linalg.inv(self.Sigma[item]) + self.p[uid][:,None]@self.p[uid][None,:])
        new_mu = new_Sigma@(np.linalg.inv(self.Sigma[item])@self.mu[item] + self.p[uid]*reward)
        new_alpha = self.alpha + 1/2
        new_beta = self.beta + 1/2*(
                self.mu[item].T @ np.linalg.inv(self.Sigma[item]) @ self.mu[item]+reward*reward - new_mu.T@np.linalg.inv(new_Sigma)@new_mu
                )
        new_lambda_k = self.lambda_[topic]+reward
        new_eta_k = self.eta[topic,item]+reward

        self.Sigma[item] = new_Sigma
        self.mu[item] = new_mu
        self.alpha = new_alpha
        self.beta = new_beta
        self.lambda_[topic] = new_lambda_k
        self.eta[topic,item] = new_eta_k
    def sample_random_variables(self,uid,item,topic):
        self.sigma_n_2 = scipy.stats.invgamma(self.alpha,self.beta).rvs()
        self.q[item] = np.random.multivariate_normal(self.mu[item],self.sigma_n_2*self.Sigma[item])
        self.p[uid] = np.random.dirichlet(self.lambda_[uid])
        self.Phi[topic] = np.random.dirichlet(self.eta[topic])

class ICTRTS(MFInteractor):
    def __init__(self,num_particles, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_particles = num_particles
        self.parameters.extend(['num_particles'])

    def train(self,train_dataset):
        super().train(train_dataset)
        self.train_dataset = train_dataset
        self.train_consumption_matrix = scipy.sparse.csr_matrix((self.train_dataset.data[:,2],(self.train_dataset.data[:,0],self.train_dataset.data[:,1])),(self.train_dataset.num_total_users,self.train_dataset.num_total_items))

        self.num_total_items = self.train_dataset.num_total_items
        self.num_total_users = self.train_dataset.num_total_users
        # self.particles = [_Particle(self.num_total_users,self.num_total_items,self.num_lat) for i in range(self.num_particles)]
        particle = _Particle(self.num_total_users,self.num_total_items,self.num_lat)
        for i in tqdm(range(len(self.train_dataset.data))):
            uid = int(self.train_dataset.data[i,0])
            item = int(self.train_dataset.data[i,1])
            reward = self.train_dataset.data[i,2]
            topic = particle.select_z_topic(uid,item,reward)
            particle.update_parameters(uid,item,reward,topic)
            particle.sample_random_variables(uid,item,topic)
            # if i > 1000:
                # break
            # self.update(uid,item,reward,None)

        self.particles = [copy.deepcopy(particle) for _ in range(self.num_particles)]
        
    def predict(self,uid,candidate_items,num_req_items):
        items_score = np.zeros(len(candidate_items))
        for particle in self.particles:
            # print(particle.p[uid].shape,particle.q[candidate_items].shape)
            items_score += particle.q[candidate_items,:]@particle.p[uid,:]
        items_score/=self.num_particles
        return items_score, None

    def update(self,uid,item,reward,additional_data):
        # for particle in self.particles:
        # with np.errstate(under='ignore'):
        weights = [particle.particle_weight(uid,item,reward) for particle in self.particles]
        weights=np.array(weights)
        weights=_softmax(weights)
        # copy.deepcopy
        ds = np.random.choice(range(self.num_particles), p=weights,size=self.num_particles)
        new_particles = []
        for i in range(self.num_particles):
            new_particles.append(copy.deepcopy(self.particles[ds[i]]))
        self.particles = new_particles
        for particle in self.particles:
            topic = particle.select_z_topic(uid,item,reward)
            particle.update_parameters(uid,item,reward,topic)
            particle.sample_random_variables(uid,item,topic)
