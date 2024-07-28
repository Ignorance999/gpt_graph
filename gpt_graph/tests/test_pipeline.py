# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 15:57:04 2024

@author: User
"""

import pytest
import numpy as np
from gpt_graph.core.decorators.component import component
from gpt_graph.core.group import Group
from gpt_graph.core.session import Session
from gpt_graph.core.pipeline import Pipeline


# Helper class and functions
class z:
    def __init__(self):
        self.z = 0

    def run(self):
        self.z += 1
        return self.z


@component(
    step_type="node_to_list",
    cache_schema={
        "z": {
            "key": "[cp_or_pp.name]",
            "initializer": lambda: z(),
        }
    },
)
def f4(x, z, y=1):
    return x + y + z.run(), x - y + z.run()


@component(step_type="list_to_node")
def f5(x):
    return np.sum(x)


@component(
    step_type="node_to_list",
    cache_schema={"z": {"key": "[base_name]", "initializer": lambda: z()}},
)
def f6(x, z):
    return [x, x - z.run(), x - z.run()]


# Test cases
def test_1_simple_pipeline_execution():
    s = Session()
    s.f4 = f4()
    s.f6 = f6()
    s.f5 = f5()
    s.p6 = s.f4 | s.f6 | s.f5
    result = s.p6.run(input_data=10)
    assert result == [59]  # Based on the test result provided


def test_2_pipeline_with_group():
    s = Session()
    s.f4 = f4()
    s.f6 = f6()
    s.f5 = f5()
    g = Group(
        filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
        parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
    )
    s.p6 = s.f4 | s.f6 | s.f5.prepend(g)
    result = s.p6.run(input_data=10)
    assert result == [33, 26]  # Based on the test result provided


def test_3_pipeline_with_group():
    s = Session()
    s.f4 = f4()
    s.f6 = f6()
    s.f5 = f5()
    g = Group(
        filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
        parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
    )
    s.p6 = s.f4 | s.f6 | s.f5.update_input_schema({"x": {"group": g}})
    result = s.p6.run(input_data=10)
    assert result == [33, 26]  # Based on the test result provided


def test_4_pipeline_connection_and_introspection():
    s3 = Session()
    s3.f4 = f4()
    s3.f6 = f6()
    s3.f5 = f5()
    g = Group(
        filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
        parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
    )
    s3.p6 = s3.f4 | s3.f6 | s3.f5.prepend(g)
    s3.p3 = s3.p6 | s3.p6

    r2 = s3.p3.run(input_data=10)
    assert r2 == [100, 93, 77, 70], f"Expected [100, 93, 77, 70], but got {r2}"


def test_5_pipeline_composition():
    from gpt_graph.tests.components.test_pp import test_pp

    p = test_pp()

    s5 = Session()
    s5.p = p

    s5.p2 = s5.p | s5.p

    r3 = s5.p2.run(input_data=10)

    assert r3 == [24, 14, 14, 4], f"Expected [24, 14, 14, 4], but got {r3}"


def test_6_complex_pipeline_with_input_initializers():
    from gpt_graph.core.components.input_initializer import InputInitializer

    s = Session()
    s.i0 = InputInitializer()
    s.i1 = InputInitializer()
    s.i2 = InputInitializer()
    s.i3 = InputInitializer()

    @component(
        step_type="list_to_node",
        input_schema={"x": {"dim": -1}, "z": {"dim": 0}, "y": {"dim": -1}},
    )
    def m0(x, y, z):
        return sum(x) + sum(y) + z

    s.m0 = m0()

    s.p = s.i0 | [s.i3, s.i1, s.i2] | s.m0

    r = s.p.run(
        input_data={"i3": 1, "i1": 2, "i2": 3}, params={"i0:input_format": "dict"}
    )

    assert r == [6], f"Expected 6, but got {r}"
   



# Define the test
# def test_7_pp_pipeline():
#     # Define the pipeline class
#     class pp(Pipeline):
#         def __init__(self):
#             super().__init__()
    
#         @component(bindings="InputInitializer")
#         def x(self, input_value):
#             return input_value + 10
        
#     # Create an instance of the pipeline
#     pp2 = pp()

#     # Run the pipeline with input_data
#     result = pp2.run(input_data={"input_value": 10})
    
#     # Assert the result
#     assert result == [20], f"Expected [20], but got {result}"

# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
    #test_1_simple_pipeline_execution()
    #test_2_pipeline_with_group()
    #test_3_pipeline_with_group()
    #test_4_pipeline_connection_and_introspection()
    #test_5_pipeline_composition()
    #test_6_complex_pipeline_with_input_initializers()
