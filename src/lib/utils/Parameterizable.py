from . import util
class Parameterizable:
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = []
    def get_id(self,num_bars=0):
        return self.__class__.__name__+':{'+util.dict_to_str(
            {i: (getattr(self,i) if not isinstance(getattr(self,i),Parameterizable) else getattr(self,i).get_id())
             for i in self.parameters}
            ,num_bars)+'}'
