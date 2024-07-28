from gpt_graph.core.step_graph import StepGraph
import inspect
from typing import Any
from gpt_graph.core.step import Step
from gpt_graph.core.closure import Closure
from gpt_graph.core.graph import Graph
import copy
import re
from gpt_graph.utils.mql import mql
from gpt_graph.utils.uuid_ex import uuid_ex
from gpt_graph.core.group import Group
import time


class Component(Closure):
    step_type = "node_to_node"
    input_schema = {"input": {"type": Any}}
    cache_schema = {}
    output_schema = {"result": {"type": Any}}
    output_format = "plain"
    bindings = None

    def __init__(
        self,
        func=None,
        base_name=None,
        namespace=None,
        lid=None,
        node_graph=None,
        step_graph=None,
        if_auto_detect_input=False,
        step_type=None,
        input_schema=None,
        output_schema=None,
        cache_schema=None,
        output_format=None,
        appended_actions=None,  # append dict
        prepended_actions=None,  # prepend=None,
        bindings=None,
        linkings=None,
        contains_lvl=0,
        clones_lvl=0,
        if_dynamic=True,
        if_inplace=None,
        if_load_env=False,
        **kwargs,
    ):
        """
        base_name is defined in Closure __init__, now redefine
        Declared: base_name, namespace, name, full_name, uuid, contains, contains_lvl
            contains_graph, rel_graph, contained, all_cps, all_params, config, if_load_env, placeholders

        This init will declare:
            lid, prototype, category, if_pp, clones_lvl, clones, global_config, steps, config_keys,
            step_type, cache_schema, output_schema, output_format, bindings, linkings, binding_step_names,
            linking_group, appended_actions, if_auto_detect_input, params, input_schema, node_graph, step_graph, if_dynamic, cache

        WARNING: be careful about assigning Component() to self attributes in __init__
                unless you are sure you are triggering __post_init__ in Closure
        """

        if base_name:
            self.base_name = base_name
        elif func is not None:
            self.base_name = func.__name__
        else:
            self.base_name = self.__class__.__name__

        self.lid = lid
        self.prototype = None  # Original cp from which this cp was prototype

        super().__init__(
            base_name=self.base_name,
            namespace=namespace,
            if_load_env=if_load_env,
        )

        # category is used in step to determine how it is runned.
        # category contains class/static/method
        self.category = None
        if func:
            self.set_run(func, if_replace_base_name=False)
        else:
            if inspect.ismethod(self.run):
                self.category = "class"
            else:
                self.category = "static"

        # if it is a pipeline
        self.if_pp = self._init_if_pp()

        # self.contains_lvl = contains_lvl
        self.clones_lvl = clones_lvl
        self.clones = []  # prototype cps

        self.global_config = {}
        self.steps = []  # {}

        self.config_keys = [
            "step_type",
            "input_schema",
            "cache_schema",
            "output_schema",
            "output_format",
            "bindings",
            "global_config",
        ]

        if step_type:
            self.step_type = step_type
        else:
            class_step_type = self.__class__.step_type
            self.step_type = (
                class_step_type[0]
                if isinstance(class_step_type, list)
                else class_step_type
            )

        self.cache_schema = cache_schema or self.__class__.cache_schema
        self.output_schema = output_schema or self.__class__.output_schema

        self.output_format = output_format or self.__class__.output_format
        self.output_format = (
            self.output_format[0]
            if isinstance(self.output_format, list)
            else self.output_format
        )

        self.bindings = bindings or self.__class__.bindings
        self.linkings = linkings

        # the following are used for special connect situation
        # [a,b,c] | d -> this will set the binding of d as {..,$if_complete = True}
        # Thus, bindings step names = {0: a's name, 1: b's name, 2: c's name}
        # when calling self.if_trigger_bindings for all a,b,c,
        # binding_step_names will be filled and then d will be triggered
        self.binding_step_names = {}

        # linking group is for a | [b,c,d], it will create a Group(if_yield = True) for b,c,d
        self.linking_group = None

        self.appended_actions = appended_actions or []
        # self.prepended_actions = prepended_actions or []

        # ------------------------------------------------------------------
        # for input schema
        if self.input_schema and if_auto_detect_input:
            print(
                f"warning: component {self.name}. if_auto_detect_input is True, input_schema will be ignored"
            )

        self.if_auto_detect_input = if_auto_detect_input

        if self.category in ("static", "class"):
            ignore_fields = ["self", "kwargs", "args"]
        else:
            ignore_fields = ["kwargs", "args"]

        if self.if_auto_detect_input:
            self.params = self._get_func_params(
                func=self.run,
                cache_fields=[*self.cache_schema.keys()],
                if_auto_detect_input=True,
                ignore_fields=ignore_fields,
            )
            self.input_schema = {
                k: {"type": Any} for k, v in self.params.items() if v["type"] == "input"
            }
        else:
            self.input_schema = input_schema or self.__class__.input_schema
            self.params = self._get_func_params(
                func=self.run,
                if_auto_detect_input=False,
                input_fields=[*self.input_schema.keys()],
                cache_fields=[
                    *self.cache_schema.keys()
                ],  # TODO: later can flexibly turn this cache on and off by setting <CACHE>
                ignore_fields=ignore_fields,
            )

        # -----------------------------------------------------------

        # NOTE: the following graphs have to be defined, because of self.clone,
        # either the sub-graph of prototype or graph of clones will be used formally as the linkage between them
        self.node_graph = node_graph or Graph()
        self.step_graph = step_graph or StepGraph()

        # only if_dynamic == True, the cp will participate in bindings or linkings
        self.if_dynamic = if_dynamic
        # cache is universal across all pp and cp
        self.cache = {}

    def set_run(self, func=None, if_replace_base_name=False):
        """
        Set the 'run' function for this object and update related attributes.

        Args:
        func (callable, optional): Function to set as 'run'. If None, only updates base_name.
        if_replace_base_name (bool): If True, replace base_name with func's name. Default False.

        Behavior:
        - Sets 'run' attribute to func
        - Updates base_name and name if if_replace_base_name is True
        - Sets input_schema based on func's first parameter
        - Determines category ('method' or 'static') based on func signature
        """
        if func:
            self.run = func
            if if_replace_base_name:
                self.base_name = func.__name__
                self.name = f"{self.base_name}.{self.lid}"

            func_params = self._get_func_params(
                func, cache_fields=[*self.cache_schema.keys()]
            )
            if func_params:
                first_param_name = next(iter(func_params))
                self.input_schema = {first_param_name: {"type": Any}}

            sig = inspect.signature(self.run)
            params = list(sig.parameters.values())
            if params[0].name == "self":  # it is a method
                self.category = "method"
            else:
                self.category = "static"

    def clone(
        self,
        memo=None,
        shallow_copy_keys=None,
        not_copy_keys=None,
        deep_copy_keys=None,
        link_copy_keys=None,
        context=None,
        if_assign_prototype=True,
        if_reset_uuid=True,
        if_verbose=False,  # TODO: can del this later if no needed
    ):
        """
        Create a deep copy of the object with customizable copying behavior.

        Parameters:
        - memo (dict): Memoization dictionary to avoid recursive copying, should be None at the beginings
        - shallow_copy_keys (list): Attributes to be shallow copied.
        - not_copy_keys (list): Attributes to be excluded from copying.
        - deep_copy_keys (list): Attributes to be copied by the defined clone_value func.
        - link_copy_keys (list): Attributes to be linked in the clone.
        - context(dict): the key-value pairs will be set to the clone just after it is created
        - if_assign_prototype (bool): Whether to set the original as prototype.
        - if_reset_uuid (bool): Whether to reset UUID of the clone.
        - if_verbose (bool): Whether to print timing information.

        Returns:
        - A new instance of the class with copied attributes.

        Behavior:
        - Creates a new instance of the same class.
        - Copies attributes based on specified keys and methods.
        - Handles nested Component, Graph, and Group objects.
        - Manages circular references using memoization.
        - Optionally assigns the original object as prototype.
        - Can reset UUID of the clone and its nested components.

        Note:
        - The method uses a combination of shallow copy, deep copy, and linking
        strategies based on the nature of each attribute.
        - Special handling is implemented for Component, Graph, Group, and uuid_ex objects.
        """
        # not_copy_keys are those following __init__ default def
        not_copy_keys = (
            not_copy_keys
            or [
                # "base_name",
                # "name",
                # "uuid",  # uuid will be generated randomly during initialization
                "clones",  # clones's clone should be empty
                # "clones_map",
                "prototype",
                "contained",
                # "contains_map",
                "all_cps",  # NOTE:this var is created by calling functions, actually, can copy it with link later
                # "node_graph",  # related to node
                "steps",
                # "step_graph",  # related to step
                # "groups"
                # contains
                # "node_graph",
                # "step_graph",
            ]
        )
        # shallow_copy_keys are those global settings
        shallow_copy_keys = shallow_copy_keys or [
            # "bindings",
            # "prototype",
            # "session",
            "global_config",
            "cache",
        ]

        deep_copy_keys = deep_copy_keys or [
            "input_schema",
            "contains",
            "bindings",
            "uuid",
        ]
        link_copy_keys = link_copy_keys or [
            "node_graph",
            "step_graph",
        ]

        if memo is None:
            memo = {}

        obj_id = id(self)
        if obj_id in memo:
            return memo[obj_id]

        clone_kwargs = {}
        if getattr(self, "if_pp", False):
            clone_kwargs["if_input_initialize"] = False

        clone = self.__class__(**clone_kwargs)
        if isinstance(context, dict):
            for k, v in context.items():
                setattr(clone, k, v)

        memo[obj_id] = clone

        def clone_value(value, link_target=None):
            """
            Creates a deep copy of the given value with special handling for certain types.

            Handles:
            - Component, Group: Uses their clone methods
            - Graph, uuid_ex: Links to target if provided, else creates new copy
            - dict, list, tuple: Recursively clones contents
            - Other types: Returns original value

            Args:
            value: Value to clone
            link_target: Optional target to link instead of copying (for Graph, uuid_ex)

            Returns:
            Cloned value

            Note: Uses memoization to handle circular references.
            """
            if isinstance(value, (Component, Graph, uuid_ex, Group)):
                value_id = id(value)
                if value_id in memo:
                    return memo[value_id]

                if isinstance(value, Component):
                    return value.clone(memo=memo)
                elif isinstance(value, Group):
                    return value.clone()
                elif isinstance(value, (Graph, uuid_ex)) and link_target is not None:
                    memo[value_id] = link_target
                    return link_target
                else:
                    new_value = copy.deepcopy(value)
                    if isinstance(new_value, uuid_ex):
                        new_value.new()
                    memo[value_id] = new_value
                    return new_value
            elif isinstance(value, (dict, list, tuple)):
                if isinstance(value, dict):
                    return {
                        k: clone_value(v, link_target.get(k) if link_target else None)
                        for k, v in value.items()
                    }
                elif isinstance(value, list):
                    return [
                        clone_value(item, link_target[i] if link_target else None)
                        for i, item in enumerate(value)
                    ]
                else:  # tuple
                    return tuple(
                        clone_value(item, link_target[i] if link_target else None)
                        for i, item in enumerate(value)
                    )
            else:
                return value

        for key, value in vars(self).items():
            if key in not_copy_keys:
                continue
            elif key in shallow_copy_keys:
                setattr(clone, key, value)
            elif key in deep_copy_keys:
                setattr(clone, key, clone_value(value))
            elif key in link_copy_keys:
                setattr(clone, key, clone_value(value, link_target=getattr(clone, key)))
            else:  # also deep copy, but not using clone_value function
                if if_verbose:
                    start_time = time.time()
                    setattr(clone, key, copy.deepcopy(value))
                    end_time = time.time()
                    print(
                        f"{self.full_name}, Deep copying '{key}' took {end_time - start_time:.4f} s"
                    )
                else:
                    setattr(clone, key, copy.deepcopy(value))

        if if_assign_prototype:
            clone.prototype = self
            self.clones.append(clone)

        if if_reset_uuid:
            clone.reset_uuid(if_recursive=True)

        return clone

    def _init_if_pp(self):
        mro_names = [c.__name__ for c in type(self).__mro__]
        if "Component" not in mro_names:
            raise
        if_pp = "Pipeline" in mro_names

        return if_pp

    def connect(
        self,
        cp_or_pp,
        if_auto_binding=True,
        if_bindings_complete=True,
    ):
        from gpt_graph.core.pipeline import Pipeline

        pipeline = Pipeline()
        pipeline.connect(
            cp_or_pp=self,
            if_inplace=True,
            if_clone_cp=True,
            if_auto_binding=if_auto_binding,
            if_bindings_complete=if_bindings_complete,
        )
        pipeline.connect(
            cp_or_pp=cp_or_pp,
            if_inplace=None,
            if_clone_cp=True,
            if_auto_binding=if_auto_binding,
            if_bindings_complete=if_bindings_complete,
        )
        return pipeline

    def get_name(self):
        """
        override Closure method, used in refresh_full_name
        """
        if not self.prototype:  # so self is prototype
            name = self.base_name
        elif (
            self.lid is None or self.base_name is None
        ):  # this condition usually occurs when self is not assigned in Sessino or contained in other pp
            name = self.uuid
        else:
            name = f"{self.base_name}.{self.lid}"

        self.name = name
        return self.name

    def get_full_name(self):
        """
        override Closure method, used in refresh_full_name
        """
        if not self.namespace:
            self.full_name = self.name
        else:
            self.full_name = f"{self.namespace};{self.name}"
        return self.full_name

    def refresh_full_name(self, namespace=None, if_recursive=True):
        """overriding Closure method"""
        if namespace is not None:
            self.namespace = namespace

        # refresh name
        self.name = self.get_name()
        self.full_name = self.get_full_name()

        for cp in self.contains:
            cp.refresh_full_name(
                namespace=self.full_name,
                if_recursive=True,
            )

    def rename(
        self,
        new_base_name=None,
        new_lid=None,
        new_namespace=None,
        if_recursive=True,
    ):
        """
        Renames the object and updates related properties.

        Args:
        new_base_name: New base name (optional)
        new_lid: New logical ID (optional)
        new_namespace: New namespace (optional)
        if_recursive: Whether to rename clones recursively (default True)

        Updates base_name and lid if provided. Refreshes full_name with new namespace.
        Recursively renames clones if if_recursive is True. Updates steps and step_graph
        if present.

        Returns:
        str: Updated full name
        """
        self.base_name = new_base_name if new_base_name is not None else self.base_name
        self.lid = new_lid if new_lid is not None else self.lid

        self.refresh_full_name(namespace=new_namespace, if_recursive=True)

        if new_base_name and if_recursive:
            for cp in self.clones:
                cp.rename(
                    new_base_name=new_base_name,
                    if_recursive=False,
                )

        if getattr(self, "steps", None) is not None:
            for step in self.steps:
                step.refresh_full_name()
            if self.step_graph:
                self.step_graph.refresh_node_names()

        return self.full_name

    def run(self):
        """Abstract method that should be implemented by subclasses.
        it can be staticmethod, a normal function or a self method
        determined by self.category
        """
        pass

    def if_trigger_linkings(self, linkings=None, next_cp=None):
        """
        used in last part in Pipeline.run, check if self will route to the next cp
        """
        linkings = linkings or self.linkings
        return self._evaluate_conditions(linkings, next_cp, is_linking=True)

    def if_trigger_bindings(self, bindings=None, previous_step=None):
        """
        used in last part in Pipeline.run, check if self is binding to the prev step
        """
        bindings = bindings or self.bindings
        return self._evaluate_conditions(bindings, previous_step, is_linking=False)

    def _evaluate_conditions(self, conditions, step_or_cp, is_linking=False):
        """
        Evaluates conditions for dynamic binding or linking.

        Args:
        conditions: Single condition or list of conditions to evaluate
        step_or_cp: Step or component to evaluate against
        is_linking: Whether this is for linking (default False)

        Processes conditions:
        - String: Matches against name, query = {"name": {"$regex": pattern}}
        - Dict: Used as query
        - None: Always False

        For binding (is_linking=False):
        - step_or_cp is step
        - For conditions with '$if_complete':
            - NOTE: this is to handle connection situation: [a,b,c] | d, all a,b,c is processed before d can
            - If condition is met, adds step_or_cp.base_name to self.binding_step_names
            - Checks if all '$if_complete' conditions are satisfied
        - If all satisfied, updates self.input_schema with self.binding_step_names

        For linking (is_linking=True):
        - step_or_cp is cp
        - If any '$if_complete' condition is met:
            - NOTE: this is to handle connection situation: d | [a,b,c], d's nodes need to have diff names
            - Creates self.linking_group if not exists
            - Updates step_or_cp's input_schema to use self.linking_group

        Returns:
        bool: True if conditions are met, False otherwise
        """
        # TODO: the curr way of handling $if_complete and [a,b,c] | d / d | [a,b,c] is BAD. try to think a better way

        if not self.if_dynamic or not conditions:
            return False

        def evaluate_single_condition(condition):
            if isinstance(condition, str):
                escaped_condition = re.escape(condition)
                pattern = f"\\b{escaped_condition}\\b"
                query = {"name": {"$regex": pattern}}
            elif isinstance(condition, dict):
                query = condition
            elif condition is None:
                return False
            else:
                raise ValueError(f"Unsupported condition type: {type(condition)}")
            return bool(mql([step_or_cp], query))

        if not isinstance(conditions, list):
            return evaluate_single_condition(conditions)

        if not any(evaluate_single_condition(c) for c in conditions):
            return False

        if not is_linking:  # bindings case
            for i, condition in enumerate(conditions):
                if "$if_complete" in condition:
                    if i not in self.binding_step_names and evaluate_single_condition(
                        condition
                    ):
                        self.binding_step_names[i] = step_or_cp.base_name  # full_name
                else:
                    result = evaluate_single_condition(condition)
                    if result:
                        return result
            result = len(self.binding_step_names) == len(
                [c for c in conditions if "$if_complete" in c]
            )
            if result:
                self.update_input_schema(
                    input_schema={
                        k: {
                            "filter_cri": {
                                "step_name": {
                                    "$regex": i,
                                    "$order": -1,
                                }
                            }
                        }
                        for i, k in zip(
                            self.binding_step_names.values(), self.input_schema.keys()
                        )
                    }
                )
            return result
        else:  # linking
            for i, condition in enumerate(conditions):
                result = evaluate_single_condition(condition)
                if result:
                    if "$if_complete" in condition:  # need dispatch
                        break
                    else:
                        return result

            if self.linking_group is None:
                self.linking_group = Group(
                    filter_cri={"step_name": {"$regex": self.base_name, "$order": -1}},
                    group_key="name",
                    if_yield=True,
                )

            step_or_cp.update_input_schema(
                input_schema={
                    k: {"group": self.linking_group}
                    for k in step_or_cp.input_schema.keys()
                }
            )
            return result

    def update_input_schema(self, input_schema):
        """
        Updates the object's input schema with new or modified entries.

        Args:
        input_schema (dict): New schema entries to update or add

        Behavior:
        - Existing keys: Updates their values, cloning 'group' entries
        - New keys: Adds them to the schema

        Returns:
        self: Allows for method chaining

        Note:
        currently used in if_trigger_linkings/bindings
        can also be used directly in chaining cp: a | b.update_input_schema({"x":{"group":g}})
        """
        for key, value in input_schema.items():
            if key in self.input_schema:
                if key == "group":
                    value = value.clone()
                # If the key already exists, update its dictionary
                self.input_schema[key].update(value)
            else:
                # If it's a new key, add it to the schema
                self.input_schema[key] = value
        return self

    def prepend(self, action, if_clone=True):
        """
        usage: a | b.prepend(Group(...)) -> same as b.update(input_schema={any input keys with dim 0 ...})
        """
        # TODO: can add other actions later;
        # currently self.prepended_actions are useless

        if isinstance(action, Group):
            for key, value in self.input_schema.items():
                if isinstance(value, dict) and value.get("dim", 0) == 0:
                    self.input_schema[key]["group"] = (
                        action.clone() if if_clone else action
                    )

        return self

    def create_step(
        self,
        params={},
        bindings=None,
        parent_ids=None,
        gid=None,
        if_ult_input=False,
    ):
        """
        Creates and appends a new Step to the current object's steps.

        Args:
        params (dict): Additional parameters to update the step's params
        bindings (optional): Custom bindings for the step
        parent_ids (optional): IDs of parent steps; only for checking purposes.
        gid (optional): Global ID for the step; seems useless
        if_ult_input (bool): If True, sets input params as ultimate

        Behavior:
        - Combines object attributes and provided params to configure the step
        - Creates a new Step instance with combined configuration
        - Appends the new Step to self.steps

        Returns:
        Step: The newly created and appended Step instance
        """
        # TODO: later should think of a way to use parent_ids
        keys = [
            "step_type",
            "input_schema",
            "cache_schema",
            "output_schema",
            "output_format",
            # "bindings", TODO: may be deprecated, as only cp need this, cp do not need to pass to step
            "global_config",
            "cache",
        ]
        config = {k: getattr(self, k) for k in keys}
        # if bindings is not None:
        #    config["bindings"] = bindings

        cp_params = self.params
        cp_params.update(params)

        step = Step(
            cp_or_pp=self,
            category=self.category,
            gid=gid,  # TODO: Step.gid can be removed later. seems useless
            lid=len(self.steps),
            node_graph=self.node_graph,
            params=cp_params,
            if_dynamic=self.if_dynamic,
            parent_ids=parent_ids,
            **config,
        )
        if if_ult_input:
            step.set_input_params_ult()

        self.steps.append(step)
        return step

    @staticmethod
    def _get_func_params(
        func,
        input_fields=["input"],
        cache_fields=[],
        ignore_fields=["self", "kwargs", "args"],
        if_auto_detect_input=False,
    ):
        """
        Extracts info about a function's parameters.

        Args:
            func (function): The function to inspect.
            input_fields (list[str]): Params considered as input. Defaults to `["input"]`.
            cache_fields (list[str]): Params considered as cache. Defaults to [].
            ignore_fields (list[str]): Params to ignore. Defaults to ["self", "kwargs", "args"].
            if_auto_detect_input (bool): Auto-detect input params. Defaults to False.

        Returns:
            dict: Dict with param names as keys and details as values:
                - type (str): "input" or "param".
                - status (str): "input", "default", "empty", "cache".
                - value: Default value or placeholder.

        Example:
            def my_func(a, b=2, input="test",d="<CACHE>"):
                pass

            _get_func_params(my_func, input_fields=["input"], cache_fields=["cp"])
            # Output:
                {'a': {'placeholder': None,
                    'priority': 0,
                    'status': 'empty',
                    'type': 'param',
                    'value': '<EMPTY>'},
                'b': {'placeholder': None,
                    'priority': 0,
                    'status': 'default',
                    'type': 'param',
                    'value': 2},
                'd': {'placeholder': None,
                    'priority': 0,
                    'status': 'cache',
                    'type': 'param',
                    'value': '<CACHE>'},
                'input': {'placeholder': None,
                        'priority': 1000,
                        'status': 'input',
                        'type': 'input',
                        'value': '<INPUT>'}}
        note:
            # param type
            # 1. type: input/ param/
            # 2. status: input/ empty/ default/ assigned/ ult_input(this is not assigned here)/ cache
            # 3  value: <INPUT> or <EMPTY> or <CACHE>
            # 4. priority: >= 1000 manual change; otherwise auto change from param files
            # 5. placeholder: [key...], will affect value when [key...] is set
        """

        input_fields = set(input_fields or [])
        ignore_fields = set(ignore_fields or [])

        signature = inspect.signature(func)

        params = {}
        for param in signature.parameters.values():
            if param.name == "cp":
                raise ValueError("cp as param is banned, it is used in cache")
            if param.name not in ignore_fields:
                param_info = {}
                param_info["placeholder"] = None

                if if_auto_detect_input:
                    if param.name in cache_fields:
                        param_info["type"] = "param"
                        param_info["status"] = "cache"
                        param_info["value"] = "<CACHE>"
                        param_info["priority"] = 0

                    elif param.default is inspect.Parameter.empty:
                        param_info["type"] = "input"
                        param_info["status"] = "input"
                        param_info["value"] = "<INPUT>"
                        param_info["priority"] = 1000
                    else:
                        param_info["type"] = "param"
                        param_info["status"] = "default"
                        param_info["value"] = param.default
                        param_info["priority"] = 0
                else:
                    # Determine the type
                    if param.name in input_fields:
                        param_info["type"] = "input"
                    else:
                        param_info["type"] = "param"

                    # Determine the status
                    if param.name in input_fields:
                        param_info["status"] = "input"
                        param_info["value"] = "<INPUT>"
                        param_info["priority"] = 1000
                    elif (
                        param.name in cache_fields and param.default == "<CACHE>"
                    ):  # NOTE: be very careful here
                        param_info["status"] = "cache"
                        param_info["value"] = "<CACHE>"
                        param_info["priority"] = 0
                    elif param.default is not inspect.Parameter.empty:
                        param_info["status"] = "default"
                        param_info["value"] = param.default
                        param_info["priority"] = 0
                    else:
                        param_info["status"] = "empty"
                        param_info["value"] = "<EMPTY>"
                        param_info["priority"] = 0

                params[param.name] = param_info

        return params

    def params_check(self, if_verbose=True):
        """
        Check if all parameters are filled (status not empty).

        Args:
            if_verbose (bool): If True, print messages for empty parameters.
        """
        for k, v in self.params.items():
            if v["status"] == "empty":
                if if_verbose:
                    print(f"Param {k} is empty")
                return False
        return True

    def __or__(self, cp_or_pp):
        return self.connect(
            cp_or_pp,
            if_auto_binding=True,
        )

    def __add__(self, cp_or_pp):
        return self.connect(
            cp_or_pp,
            if_auto_binding=False,
        )

    def __ror__(self, cp_or_pp):
        from gpt_graph.core.pipeline import Pipeline

        # This method is called for right-side OR operations
        pipeline = Pipeline()
        pipeline.connect(
            cp_or_pp=cp_or_pp,
            if_inplace=True,
            if_clone_cp=True,
            if_auto_binding=True,
        )
        pipeline.connect(
            cp_or_pp=self,
            if_inplace=None,
            if_clone_cp=True,
            if_auto_binding=True,
        )
        return pipeline

    def __repr__(self):
        return f"<{self.__class__.__name__}(full_name={self.full_name}, base_name={self.base_name}, name={self.name}, uuid = {self.uuid})>"
