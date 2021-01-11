from os.path import dirname, realpath, sep, pardir
import sys
sys.path.append(dirname(realpath(__file__)) + sep + pardir + sep + "lib")

import inquirer
import utils.dataset as dataset
import yaml
import utils.dataset_parsers as dataset_parsers
import utils.splitters as splitters

with open("settings"+sep+"datasets_preprocessors.yaml") as f:
    loader = yaml.SafeLoader
    datasets_preprocessors = yaml.load(f,Loader=loader)
    
    datasets_preprocessors = {setting['name']:setting
                               for setting in datasets_preprocessors}
    q = [
        inquirer.List(0,
                          message='Datasets Preprocessors',
                          choices=datasets_preprocessors.keys()
                          )
    ]
    answers=inquirer.prompt(q)
    dataset_preprocessor = datasets_preprocessors[answers[0]]

    dataset_descriptor=dataset.DatasetDescriptor(dataset_preprocessor['name'],
                              dataset_preprocessor['dataset_dir'])

    dataset_parser = eval('dataset_parsers.'+dataset_preprocessor['dataset_parser'])()
    dataset_parsed = dataset_parser.parse_dataset(dataset_descriptor)

    if dataset_preprocessor['splitter'] != None:
        with open("settings"+sep+"splitters.yaml") as splittersf:
            splitters_settings = yaml.load(splittersf,Loader=loader)
            splitter = eval('splitters.'+dataset_preprocessor['splitter'])(**splitters_settings[dataset_preprocessor['splitter']])
            result=splitter.apply(dataset_parsed)
    else:
        result = dataset_parsed

    
    result_file_path = os.path.join(DirectoryDependent().DIRS['dataset_preprocess'],'dspp_'+dict_to_str(dataset_descriptor)+'.pickle')
    pickle.dump(result,result_file_path)
