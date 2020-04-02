from util import dict_to_list

class Nameable():
    def get_name(self):
        list_parameters=list(map(str,dict_to_list(self.__dict__)))
        string="_" if len(list_parameters)>0 else ""
        return f"{self.__class__.__name__}"+\
            string+'_'.join(list_parameters)
