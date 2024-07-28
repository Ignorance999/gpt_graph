from gpt_graph.utils.load_env import load_env
from gpt_graph.core.closure import Closure


class Session(Closure):
    def __init__(self):
        super().__init__()
        load_env()

    def __setattr__(self, name, value):
        mro_names = [c.__name__ for c in type(value).__mro__]
        if "Closure" in mro_names:
            self.register(base_name=name, cp_or_pp=value)

        object.__setattr__(self, name, value)
