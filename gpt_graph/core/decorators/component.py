from gpt_graph.core.component import Component
from typing import Any, Dict


def component(
    step_type: str = "node_to_node",
    input_schema: Dict[str, Dict[str, Any]] = None,
    cache_schema: Dict[str, Dict[str, Any]] = {},
    output_schema: Dict[str, Dict[str, Any]] = {"result": {"type": Any}},
    output_format: str = "plain",
    bindings=None,
    **kwargs,
):
    if input_schema is None:
        if_auto_detect_input = True
    else:
        if_auto_detect_input = False

    def decorator(func):
        class DerivedComponent(Component):
            def __init__(self, *args, **init_kwargs):
                return super().__init__(
                    func=func,
                    step_type=step_type,
                    input_schema=input_schema,
                    cache_schema=cache_schema,
                    output_schema=output_schema,
                    output_format=output_format,
                    if_auto_detect_input=if_auto_detect_input,
                    bindings=bindings,
                    **kwargs,
                    **init_kwargs,
                )

        return DerivedComponent

    return decorator


# def component(
#     step_type: str = "node_to_node",
#     input_schema: Dict[str, Dict[str, Any]] = None,
#     cache_schema: Dict[str, Dict[str, Any]] = {},
#     output_schema: Dict[str, Dict[str, Any]] = {"result": {"type": Any}},
#     output_format: str = "plain",
#     **kwargs,
# ):
#     if input_schema is None:
#         if_auto_detect_input = True
#     else:
#         if_auto_detect_input = False

#     def decorator(func):
#         return Component(
#             func=func,
#             step_type=step_type,
#             input_schema=input_schema,
#             cache_schema=cache_schema,
#             output_schema=output_schema,
#             output_format=output_format,
#             if_auto_detect_input=if_auto_detect_input,
#             **kwargs,
#         )

#     return decorator
