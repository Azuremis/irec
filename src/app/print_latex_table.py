from os.path import dirname, realpath, sep, pardir
import os
import sys
sys.path.append(dirname(realpath(__file__)) + sep + pardir + sep + "lib")

import inquirer
import scipy
import interactors
import mf
from utils.InteractorRunner import InteractorRunner
from sklearn.decomposition import NMF
import numpy as np
import scipy.sparse
from utils.DatasetManager import DatasetManager
import yaml
from metric import CumulativeInteractionMetricsEvaluator, UserCumulativeInteractionMetricsEvaluator
from utils.dataset import Dataset
from utils.PersistentDataManager import PersistentDataManager
from utils.InteractorCache import InteractorCache
import metric
import matplotlib.pyplot as plt
from utils.DirectoryDependent import DirectoryDependent
from cycler import cycler
from collections import defaultdict
plt.rcParams['axes.prop_cycle'] = cycler(color='krbgmyc')
plt.rcParams['lines.linewidth'] = 2
plt.rcParams['font.size'] = 15

metrics_classes = [metric.Hits, metric.Recall]
metrics_names = ['Cumulative Hits', 'Cumulative Recall']

dm = DatasetManager()
datasets_preprocessors = dm.request_datasets_preprocessors()
# print(datasets_preprocessors_classes)

interactors_preprocessor_paramaters = yaml.load(
    open("settings" + sep + "interactors_preprocessor_parameters.yaml"),
    Loader=yaml.SafeLoader)
interactors_general_settings = yaml.load(
    open("settings" + sep + "interactors_general_settings.yaml"),
    Loader=yaml.SafeLoader)

evaluation_policies_parameters = yaml.load(
    open("settings" + sep + "evaluation_policies_parameters.yaml"),
    Loader=yaml.SafeLoader)

interactors_classes_names_to_names = {
    k: v['name'] for k, v in interactors_general_settings.items()
}

ir = InteractorRunner(dm, interactors_general_settings,
                      interactors_preprocessor_paramaters,
                      evaluation_policies_parameters)
interactors_classes = ir.select_interactors()

metrics_evaluator = UserCumulativeInteractionMetricsEvaluator(None, metrics_classes)

evaluation_policy = ir.get_interactors_evaluation_policy()

nums_interactions_to_show = [5, 10, 20, 50, 100]


def generate_table_spec():
    res = '|'
    for i in range(1 + len(nums_interactions_to_show) *
                   len(datasets_preprocessors)):
        res += 'c'
        if i % (len(nums_interactions_to_show)) == 0:
            res += '|'
    return res


rtex_header = r"""
\documentclass{article}
\usepackage[landscape, paperwidth=15cm, paperheight=30cm, margin=0mm]{geometry}
\usepackage{multirow}
\usepackage{color, colortbl}
\usepackage{xcolor, soul}
\usepackage{amssymb}
\definecolor{Gray}{gray}{0.9}
\definecolor{StrongGray}{gray}{0.7}
\begin{document}
\begin{tabular}{%s}
\hline
\rowcolor{StrongGray}
Dataset & %s \\""" % (generate_table_spec(), ' & '.join([
    r"\multicolumn{%d}{c|}{%s}" % (len(nums_interactions_to_show), i['name'])
    for i in datasets_preprocessors
]))
rtex_footer = r"""
\end{tabular}
\end{document}
"""
rtex = ""

datasets_metrics_values = defaultdict(
    lambda: defaultdict(lambda: defaultdict(list)))

datasets_metrics_users_values = defaultdict(
    lambda: defaultdict(lambda: defaultdict(list)))

for dataset_preprocessor in datasets_preprocessors:
    dm.initialize_engines(dataset_preprocessor)

    for metric_class_name in map(lambda x: x.__name__, metrics_classes):
        for itr_class in interactors_classes:
            itr = ir.create_interactor(itr_class)
            pdm = PersistentDataManager(directory='results')

            metrics_pdm = PersistentDataManager(directory='metrics')
            metric_values = metrics_pdm.load(
                os.path.join(
                    InteractorCache().get_id(dm, evaluation_policy, itr),
                    metrics_evaluator.get_id(), metric_class_name))
            datasets_metrics_values[dataset_preprocessor['name']][
                metric_class_name][itr_class.__name__].extend(
                    [np.mean(metric_values[i - 1]) for i in nums_interactions_to_show])
            datasets_metrics_users_values[dataset_preprocessor['name']][
                metric_class_name][itr_class.__name__].extend(
                    np.array([metric_values[i - 1] for i in nums_interactions_to_show]))

import copy
datasets_metrics_gain = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: ['']*len(nums_interactions_to_show))))
bullet_str = r'\textcolor[rgb]{0.7,0.7,0.0}{$\bullet$}'
triangle_up_str = r'\textcolor[rgb]{00,0.45,0.10}{$\blacktriangle$}'
triangle_down_str = r'\textcolor[rgb]{0.7,00,00}{$\blacktriangledown$}'
for dataset_preprocessor in datasets_preprocessors:
    for metric_class_name in map(lambda x: x.__name__, metrics_classes):
        for i, num in enumerate(nums_interactions_to_show):
        # for itr_class in interactors_classes:
            best_itr = max(datasets_metrics_values[dataset_preprocessor['name']][
                metric_class_name].items(),key=lambda x: x[1][i])[0]
            best_itr_vals = datasets_metrics_values[dataset_preprocessor['name']][
                    metric_class_name].pop(best_itr)
            best_itr_val = best_itr_vals[i]
            second_best_itr = max(datasets_metrics_values[dataset_preprocessor['name']][
                metric_class_name].items(),key=lambda x: x[1][i])[0]
            second_best_itr_vals = datasets_metrics_values[dataset_preprocessor['name']][
                    metric_class_name][second_best_itr]
            second_best_itr_val = second_best_itr_vals[i]
            # come back with value in dict
            datasets_metrics_values[dataset_preprocessor['name']][

                    metric_class_name][best_itr] = best_itr_vals

            best_itr_users_val = datasets_metrics_users_values[dataset_preprocessor['name']][
                metric_class_name][best_itr][i]
            second_best_itr_users_val = datasets_metrics_users_values[dataset_preprocessor['name']][
                metric_class_name][second_best_itr][i]

            statistic, pvalue = scipy.stats.wilcoxon(
                    best_itr_users_val,
                    second_best_itr_users_val,
                    )

            if pvalue > 0.05:
                datasets_metrics_gain[dataset_preprocessor['name']][metric_class_name][best_itr][i]=bullet_str
            else:
                if best_itr_val < second_best_itr_val:
                    datasets_metrics_gain[dataset_preprocessor['name']][metric_class_name][best_itr][i]=triangle_down_str
                elif best_itr_val > second_best_itr_val:
                    datasets_metrics_gain[dataset_preprocessor['name']][metric_class_name][best_itr][i]=triangle_up_str
                else:
                    datasets_metrics_gain[dataset_preprocessor['name']][metric_class_name][best_itr][i]=bullet_str


for metric_name, metric_class_name in zip(
        metrics_names, map(lambda x: x.__name__, metrics_classes)):
    rtex += r"""
\hline
\hline
\rowcolor{Gray}
Measure & %s \\
\hline
\rowcolor{Gray}
T & %s \\
\hline
\hline
""" % (' & '.join(
        map(
            lambda x: r"\multicolumn{%d}{c|}{%s}" %
            (len(nums_interactions_to_show), x),
            [metric_name] * len(datasets_preprocessors))), ' & '.join(
                [' & '.join(map(str, nums_interactions_to_show))] *
                len(datasets_preprocessors)))
    for itr_class in interactors_classes:
        rtex += "%s & " % (ir.get_interactor_name(itr_class.__name__))
        rtex += ' & '.join([
            ' & '.join(
                map(
                    lambda x,y: f"{x:.4f}{y}",
                    datasets_metrics_values[dataset_preprocessor['name']]
                    [metric_class_name][itr_class.__name__],
                    datasets_metrics_gain[dataset_preprocessor['name']][metric_class_name][itr_class.__name__]
                    ))
            for dataset_preprocessor in datasets_preprocessors
        ])
        rtex += r'\\\hline' + '\n'

res = rtex_header + rtex + rtex_footer

tmp = '_'.join([
    dataset_preprocessor['name']
    for dataset_preprocessor in datasets_preprocessors
])
open(os.path.join(DirectoryDependent().DIRS['tex'], f'table_{tmp}.tex'),
     'w+').write(res)
os.system(
    f"pdflatex -output-directory=\"{DirectoryDependent().DIRS['pdf']}\" \"{os.path.join(DirectoryDependent().DIRS['tex'],f'table_{tmp}.tex')}\""
)
