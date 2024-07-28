from gpt_graph.core.pipeline import Pipeline
from gpt_graph.tests.components.test_components import *


class test_pp(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.f5 = f5()
        self.f4 = f4()
        self.Testf = Testf()
        self | f5() | f4() | Testf()
