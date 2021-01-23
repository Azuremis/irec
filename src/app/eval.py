from os.path import dirname, realpath, sep, pardir
import os
import sys
sys.path.append(dirname(realpath(__file__)) + sep + pardir + sep + "lib")

import inquirer
import interactors
import mf
from utils.InteractorRunner import InteractorRunner
from sklearn.decomposition import NMF
import numpy as np
import scipy.sparse
from utils.DatasetManager import DatasetManager
import yaml
from metric import InteractionMetricsEvaluator, CumulativeMetricsEvaluator
from utils.dataset import Dataset
from utils.PersistentDataManager import PersistentDataManager
from utils.InteractorCache import InteractorCache
import metric


metrics_classes = [metric.Precision,metric.Recall,metric.Hits]


dm = DatasetManager()
dm.request_dataset_preprocessor()
dm.initialize_engines()
dm.load()

interactors_preprocessor_paramaters = yaml.load(open("settings"+sep+"interactors_preprocessor_parameters.yaml"),Loader=yaml.SafeLoader)
interactors_general_settings = yaml.load(open("settings"+sep+"interactors_general_settings.yaml"),Loader=yaml.SafeLoader)

evaluation_policies_parameters = yaml.load(open("settings"+sep+"evaluation_policies_parameters.yaml"),Loader=yaml.SafeLoader)

ir = InteractorRunner(dm,interactors_general_settings,interactors_preprocessor_paramaters,evaluation_policies_parameters)
interactors_classes = ir.select_interactors()

data = np.vstack((dm.dataset_preprocessed[0].data,
                  dm.dataset_preprocessed[1].data))

dataset = Dataset(data)
dataset.update_from_data()
dataset.update_num_total_users_items()

metrics_evaluators = [InteractionMetricsEvaluator(dataset,metrics_classes), CumulativeMetricsEvaluator(dataset,metrics_classes)]

for metric_evaluator in metrics_evaluators:
    for itr_class in interactors_classes:
        itr = ir.create_interactor(itr_class)
        evaluation_policy = ir.get_interactor_evaluation_policy(itr)
        pdm = PersistentDataManager(directory='results')
        users_items_recommended = pdm.load(InteractorCache().get_id(dm,evaluation_policy,itr))

        metrics_pdm = PersistentDataManager(directory='metrics')
        if isinstance(metric_evaluator,InteractionMetricsEvaluator):
            metrics_values = metric_evaluator.evaluate(evaluation_policy.num_interactions,evaluation_policy.interaction_size,users_items_recommended)
        elif isinstance(metric_evaluator,CumulativeMetricsEvaluator):
            metrics_values = metric_evaluator.evaluate(users_items_recommended)

        for metric_name, metric_values in metrics_values.items():
            metrics_pdm.save(os.path.join(InteractorCache().get_id(dm,evaluation_policy,itr),metric_evaluator.NAME_ABBREVIATION,metric_name),metric_values)
