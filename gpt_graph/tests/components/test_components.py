from gpt_graph.core.component import Component
from gpt_graph.core.decorators.component import component
from typing import Any
import numpy as np


@component(step_type="node_to_list")
def f4(x, y=1):
    return x + y, x - y


@component(step_type="list_to_node")
def f5(x):
    return np.sum(x)


@component(step_type="node_to_list")
def f6(x):
    return [x, x + 1]


class Testf(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"x": {"type": Any}}
    cache_schema = {}
    output_schema = {"result": {"type": Any}}
    output_format = "plain"

    @staticmethod
    def run(x, y):
        result = x + y
        return result


class Testf2(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"x": {"type": Any}}  # , "y": {"type": Any}}
    cache_schema = {}
    output_schema = {"result": {"type": Any}}
    output_format = "node_like"

    @staticmethod
    def run(x, y):
        result = x - y
        return {"content": result}


class Testf3(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"x": {"type": Any}}
    cache_schema = {}
    output_schema = {"add_result": {"type": Any}, "sub_result": {"type": Any}}
    output_format = "dict"

    @staticmethod
    def run(x, y, y2):
        add_result = x + y
        sub_result = x - y2
        return {"add_result": add_result, "sub_result": sub_result}


class Testf4(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"x": {"type": Any}, "y": {"type": Any}}
    cache_schema = {}
    output_schema = {"add_result": {"type": Any}, "sub_result": {"type": Any}}
    output_format = "dict"

    @staticmethod
    def run(x, y, y2=5):
        add_result = x + y
        sub_result = x - y2
        return {"add_result": add_result, "sub_result": sub_result}
