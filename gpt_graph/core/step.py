import sys
import logging
from gpt_graph.utils.validation import validate_type
from typing import List, Callable, Type, Any, Dict
from gpt_graph.utils.uuid_ex import uuid_ex
import re
import gpt_graph.utils as utils
from itertools import product
import types

logger = logging.getLogger(__name__)


class Step:
    def __init__(
        self,
        cp_or_pp=None,
        params={},
        gid=0,  # TODO: this may not be needed
        lid=0,
        step_type=None,
        step_id=None,
        input_schema=None,
        cache_schema=None,
        output_schema=None,
        output_format=None,
        # bindings=None, TODO: may be deprecated, as only cp need this, cp do not need to pass to step
        appended_actions=None,
        node_graph=None,
        if_dynamic=True,
        cache=None,
        global_config=None,
        parent_ids=None,
        category=None,
    ):
        """
        Initializes a step object.

        Args:
            cp_or_pp: Component or pipeline object
            params (dict): updated parameters for the Step.run function
            gid (int): Group ID (may be deprecated)
            lid (int): Local ID
            step_id (str): Unique step identifier
            step_type/input_schema/ cache_schema/ output_schema: Schema definitions
            output_format: Format specification for output
            appended_actions: Additional actions to be performed (may be deprecated)
            node_graph: Associated node graph
            if_dynamic (bool): (may be deprecated, only used in cp's linking/bindings,  no need to pass to step)
            cache (dict): Cache storage
            global_config: Global configuration settings
            parent_ids: full_name of parent steps
            category (str): Step category (static/class/method)

        Attributes:
            self.config_keys/ uuid/ cp_or_pp/ category/ cp_name/ base_name/ node_graph/ cache/ contains: Various configuration and metadata
            self.cp_run_func: Function to run the component or pipeline
            self.params/ params_key/ gid/ lid/ name/ full_name/ step_id/ step_type/ input_schema/ cache_schema/ output_schema/ output_format/ bindings/ appended_actions/ if_dynamic/ global_config/ parent_ids: Step-specific attributes
            self.next/ prev: Links to next and previous steps
            self.if_err_remove_node/ if_replace_node/ route_to: Error handling and routing configs
            self.groups/ output/ nodes: Execution-related attributes

        Possible choices:
            self.category (str): (static/class/method)
            self.status:  'running', 'finished', 'idle', 'queued'
            self.output_format:  none, graph, node(share address), node_like, dict, dict_node

        Notes:
            - Initializes a step with various configurations and metadata
            - Sets up execution function based on category (class/static/method)
        """
        # TODO: consider del bindings/ appended_actions/ if_dynamic/ gid/ self.next/prev
        self.config_keys = [
            "step_type",
            "input_schema",
            "cache_schema",
            "output_schema",
            "bindings",
            "name",
        ]
        self.uuid = uuid_ex(obj=self)

        self.cp_or_pp = cp_or_pp
        self.category = category  # static/ class/ method

        self.cp_name = cp_or_pp.full_name
        self.base_name = cp_or_pp.base_name

        self.node_graph = node_graph

        self.cache = {} if cache is None else cache

        self.contains = []

        from gpt_graph.core.pipeline import Pipeline

        if self.category == "class" or isinstance(cp_or_pp, Pipeline):

            def func(cp=None, **kwargs):
                """
                Execute a function with caching mechanism for self-referential objects.

                Args:
                    cp (object, optional): Cached object to use instead of creating a new one.
                    **kwargs: Additional arguments for the run method.

                Returns:
                    Result of clone.run()

                <SELF> Mechanism:
                WARNING: 'cp' is a special parameter in step's self.cp_run_func, do not use it as param

                1. If cp is provided, use it directly in self.cp_run_func(cached version).
                2. If <SELF> is in cache_schema:
                - Generate a cache key for <SELF>
                - If not in cache, store the clone for future use (This cp will be pluged into later self.cp_run_func)

                This allows reusing the same object across multiple calls,
                avoiding unnecessary cloning and maintaining state.
                """
                if cp is not None:
                    print("using cache cp")
                    clone = cp
                else:
                    clone = cp_or_pp.clone()
                self.contains.append(clone)
                result = clone.run(**kwargs)
                if "<SELF>" in self.cache_schema:
                    cache_key = self.get_cache_key(key="<SELF>")
                    if cache_key not in self.cache:
                        self.cache[cache_key] = clone

                return result

            self.cp_run_func = func
        elif self.category in ("static", "method"):
            self.cp_run_func = cp_or_pp.run

        self.params = params
        self.params_key = [*self.params.keys()]

        # self.gid = gid
        self.lid = lid
        self.name = self.get_name()
        self.full_name = self.get_full_name()

        self.step_id = step_id
        self.step_type = step_type
        self.input_schema = input_schema
        self.cache_schema = cache_schema
        self.output_schema = output_schema
        self.output_format = output_format
        # self.bindings = bindings
        # self.appended_actions = appended_actions
        self.if_dynamic = if_dynamic

        self.global_config = global_config
        self.parent_ids = parent_ids

        # self.next = []
        # self.prev = []

        self.if_err_remove_node = True  # default
        self.if_replace_node = (
            True  # TODO: curr no use, will be useful for continue mode of run
        )
        self.route_to = None

        self.groups = {}
        self.status = "idle"  # or 'running', 'finished', 'idle', 'queued'
        self.output = None
        self.nodes = None

    def set_input_params_ult(self, param_names=None):
        """used in Component.create_step"""
        param_names = param_names or [*self.params.keys()]
        for name in param_names:
            param = self.params[name]
            if param["type"] == "input":
                param["status"] = "ult_input"

    def run(self, group=None, step_id=None, parent_steps=None, params={}):
        """
        This function is the core of the step execution process. It handles input
        processing, runs the main computation, and manages the creation of output
        nodes in the graph.

        Parameters:
        -----------
        group : object, optional
            A group object that may contain pre-processed nodes.
        step_id : str, optional
            An identifier for the current step.
        parent_steps : list, optional
            A list of parent steps in the execution chain.
        params : dict, optional
            Additional parameters for self.cp_run_func, on top of default params.
            can write in format {"xx;xx:param_name" : value}

        Returns:
        --------
        list
            A list of newly created nodes in the graph.

        Behavior:
        ---------
        1. Initializes step information and prepares input parameters.
        2. Processes input schema to extract required data from nodes or parameters.
        3. Generates all possible combinations of input parameters.
        4. Executes the main computation function (cp_run_func) for each combination.
        5. Creates new nodes in the graph based on the computation results and output schema.
        6. Handles different output formats (node, list, graph, dict, etc.).
        7. Returns the list of newly created nodes.

        Notes:
        ------
        - The function supports various input and output types and formats.
        - It can process inputs individually or in batches.
        - The function interacts with a graph structure, adding and connecting nodes as needed.
        - Error handling (currently commented out) can be implemented to clean up in case of failures.
        """
        print(f"\nStep: {self.full_name}")
        self.step_id = step_id
        self.parent_steps = parent_steps or []

        """
        self.params have the format of
        {'input_data': {'type': 'input',
        'status': 'input',
        'value': '<INPUT>',
        'priority': 0}}
        """
        input_keys = [*self.input_schema.keys()]
        raw_params = {
            key: param["value"]
            for key, param in self.params.items()
            if key not in input_keys
        }
        raw_params.update(params)
        raw_params.update(self._handle_cache())  # params have been updated by cache

        node_ids_before = set(self.node_graph.nodes())
        step_type = self.step_type
        input_schema = self.input_schema
        output_schema = self.output_schema
        output_format = self.output_format

        def create_params_list(data):
            """
            Generate combinations of parameters and their parent nodes from structured input data.

            Args:
            data (dict): A dictionary containing parameter information.
                        Each key represents a parameter, and its value is a dict with:
                        - 'nodes': List of possible values or nested lists
                        - 'dim': Dimension for grouping (0, 1, ..., or -1 for scalars), if -1 treat as list to nodes; else node to node
                        - 'parent_nodes': Corresponding parent nodes

            Returns:
            list: Each item is a tuple (params_dict, parent_nodes_list)
                - params_dict: Combined parameter values
                - parent_nodes_list: Flattened list of corresponding parent nodes

            Logic:
            1. Separate scalar and non-scalar parameters
            2. Group non-scalar parameters by dimension
            3. Generate all combinations of non-scalar parameters
            4. For each combination:
            - Flatten the parameter values and parent nodes
            - Add scalar parameters and their parents
            5. Return list of all parameter combinations with their parent nodes

            Example:
            data = {
                "x": {"nodes": [[1,2], [2,3], [2,4]], "dim": 0, "parent_nodes": [["px1", "px2"], ["px3", "px4"], ["px5", "px6"]]},
                "y": {"nodes": [3, 4, 5], "dim": 0, "parent_nodes": ["py1", "py2", "py3"]},
                "z": {"nodes": [10, 20, [30,2]], "dim": 1, "parent_nodes": ["pz1", "pz2", ["pz3", "pz4"]]},
                "a": {"nodes": [5, 6], "dim": -1, "parent_nodes": ["pa1", "pa2"]},
                "b": {"nodes": 2, "dim": -1, "parent_nodes": "pb1"}
            }

            result = create_params_list(data)
            >>> [({'x': [1, 2], 'y': 3, 'z': 10, 'a': [5, 6], 'b': 2}, ['px1', 'px2', 'py1', 'pz1', 'pa1', 'pa2', 'pb1']),
                 ({'x': [1, 2], 'y': 3, 'z': 20, 'a': [5, 6], 'b': 2}, ['px1', 'px2', 'py1', 'pz2', 'pa1', 'pa2', 'pb1']),
                 ({'x': [1, 2], 'y': 3, 'z': [30, 2], 'a': [5, 6], 'b': 2}, ['px1', 'px2', 'py1', 'pz3', 'pz4', 'pa1', 'pa2', 'pb1'])
                 ...]
            """
            scalar_vars = {
                key: value["nodes"] for key, value in data.items() if value["dim"] == -1
            }
            scalar_parents = {
                key: value["parent_nodes"]
                for key, value in data.items()
                if value["dim"] == -1
            }
            non_scalar_vars = {
                key: value for key, value in data.items() if value["dim"] != -1
            }

            dim_groups = {}
            dim_parents = {}
            for key, value in non_scalar_vars.items():
                dim = value["dim"]
                if dim not in dim_groups:
                    dim_groups[dim] = []
                    dim_parents[dim] = []
                dim_groups[dim].append((key, value["nodes"]))
                dim_parents[dim].append((key, value["parent_nodes"]))

            dim_products = []
            parent_products = []
            for dim in sorted(dim_groups.keys()):
                group = dim_groups[dim]
                parent_group = dim_parents[dim]

                dim_combinations = list(zip(*[nodes for _, nodes in group]))
                parent_combinations = list(
                    zip(*[nodes if nodes else [None] for _, nodes in parent_group])
                )

                dim_products.append(dim_combinations)
                parent_products.append(parent_combinations)

            result = list(product(*dim_products))
            parent_result = list(product(*parent_products))

            final_result = []
            for item, parent_item in zip(result, parent_result):
                flattened = {}
                flattened_parents = []
                for dim, (values, parent_values) in enumerate(zip(item, parent_item)):
                    for (key, _), value, parent_value in zip(
                        dim_groups[dim], values, parent_values
                    ):
                        flattened[key] = value
                        if parent_value is not None:
                            flattened_parents.extend(
                                parent_value
                                if isinstance(parent_value, list)
                                else [parent_value]
                            )

                flattened.update(scalar_vars)
                for parent in scalar_parents.values():
                    if parent:  # Only extend if parent is not empty
                        flattened_parents.extend(
                            parent if isinstance(parent, list) else [parent]
                        )

                final_result.append((flattened, flattened_parents))

            return final_result

        # try:   TODO: reverse it back to try later
        if True:
            if self.if_replace_node:  # currently useless, useful later
                self.node_graph.remove_nodes({"step_name": self.full_name})

            # -----------------------------------------------------------------------
            # those cp created by @component inside pipelines (@ over self's method).
            if self.category == "method":
                with self.node_graph.record_changes() as changes:
                    self.cp_run_func(**params)
                added_nodes = changes["added_nodes"]
                for node in added_nodes:
                    if not node.get("step_id", False):
                        node["step_id"] = self.step_id
                    if not node.get("step_name", False):
                        node["step_name"] = self.full_name
                    if not node.get("cp_name", False):
                        node["cp_name"] = self.cp_name
                return added_nodes

            # -----------------------------------------------------------------------
            """
            Process input schema and params to create input_key_data.

            Args:
                input_schema (dict): Schema defining input structure and requirements.
                params (dict): Parameters for input processing.
                step_type (str): Type of processing step.
            
            Result:
                params_with_parent_list (list): List of parameters with parent nodes.

            Processes each input key in the schema:
                - Handles different input dimensions and grouping.
                - Retrieves input nodes based on filter criteria and dimensions.
                - Applies source field logic to extract relevant data from nodes.
                - Manages ultimate inputs, node/node-like inputs, and other data types.
                - Ensures consistency in node counts for inputs with the same dimension.
                - Creates a structured input_key_data dictionary and a params_with_parent_list.
                        
            Format: 
                # e.g. input_schema = {"upload_file_path": {"key": "[text]" , type": str, "field": "extra.name", "dim":-1}

                   input_key_data[input_key] = {
                    "parent_nodes": parent_nodes,
                    "nodes": processed,
                    "dim": input_dim}

                   params_with_parent_list = 
                                   [({'x': [1, 2], 'y': 3, 'z': 10,}, ['px1', 'px2']),
                                    ({'x': [1, 2], 'y': 3, 'z': 20,}, ['px1', 'px2']),
                                    ({'x': [1, 2], 'y': 3, 'z': [30, 2]}, ['px1', 'px2'])
            """

            input_key_data = {}
            count_dims = {}

            for i, (input_key, input_details) in enumerate(input_schema.items()):
                input_source_field = input_details.get("field", "content")
                input_type = input_details.get("type", Any)
                input_dim = input_details.get("dim", None)
                input_group = input_details.get("group", None)

                # if isinstance(getattr(params, input_key, False), dict):
                #    #NOTE: you can set filter_cri in normal param
                #    input_filter_cri = params[input_key]
                # else:
                input_filter_cri = input_details.get(
                    "filter_cri", {"step_id": {"$order": -1}}
                )

                if input_dim is None:
                    if (
                        step_type in ("list_to_node", "list_to_list")
                        and input_group is None
                    ):
                        input_dim = -1
                    else:
                        input_dim = 0

                if self.params[input_key]["status"] == "ult_input":
                    input_key_nodes = params.get(input_key)
                    input_key_nodes = (
                        [input_key_nodes]
                        if not isinstance(input_key_nodes, list)
                        else []
                    )
                else:
                    if input_dim == -1:
                        # when input_dim is -1, the whole list of nodes will be input into self.cp_run_func
                        input_key_nodes = self.node_graph.default_get_input_nodes(
                            input_filter_cri
                        )  # output list of nodes
                    else:
                        if input_group:
                            # if there is group in input schema, use group as input.
                            # if Group.if_yield then input_key_nodes is the nodes of one of the sub-group
                            # else, input key nodes are list of list of nodes
                            if input_group.nodes is None:
                                input_group.run(node_graph=self.node_graph)
                            input_key_nodes = (
                                input_group.get_nodes()
                            )  # if_yield value is preset

                        elif not count_dims.get(input_dim, False):
                            input_key_nodes = self.node_graph.default_get_input_nodes(
                                input_filter_cri
                            )
                        else:
                            # count_dims.get(input_dim, True)
                            # latter input need to have same number of nodes as prev input key's nodes with same dim
                            # e.g. x = (1,2,3) dim 0 ; y = (4,5,6) dim 0 -> then they can be zipped and plug into 3 self.cp_run_func

                            # get the first key with same dim
                            first_key = next(
                                (
                                    key
                                    for key, value in input_schema.items()
                                    if value.get("dim", 0) == input_dim
                                ),
                                None,
                            )
                            first_nodes = input_key_data[first_key]["nodes"]

                            # set children = first_nodes so as to match number of nodes as first nodes
                            input_key_nodes = [
                                self.node_graph.default_get_input_nodes(
                                    filter_cri=input_filter_cri,  # params.get(input_key, input_filter_cri),
                                    children=node,
                                    if_inclusive=True,
                                )
                                for node in first_nodes
                            ]
                            input_key_nodes = [
                                item for sublist in input_key_nodes for item in sublist
                            ]

                            # if prev method fails, try another method
                            if len(input_key_nodes) != len(first_nodes):
                                input_key_nodes = self.node_graph.default_get_input_nodes(
                                    filter_cri=input_filter_cri,  # params.get(input_key, input_filter_cri),
                                    if_inclusive=True,
                                )
                            if len(input_key_nodes) != len(first_nodes):
                                raise Exception("Mismatch in node count")

                # Apply source field logic for each param
                processed = []
                parent_nodes = []
                for nodes in input_key_nodes:
                    if isinstance(nodes, list):
                        # input key nodes are list of list of nodes
                        group = []
                        sub_parents = []
                        for n in nodes:
                            if (
                                input_type in ("node", "node_like")
                                or self.params[input_key]["status"] == "ult_input"
                            ):
                                # some cp receives node/node-like, where others receive numbers.
                                # For node/node-like or ult input, directly put the nodes of previous step/ input from self.run
                                group.append(n)
                            else:
                                group.append(n[input_source_field])

                            if validate_type(
                                n, "node"
                            ):  # TODO: utils module, may change lataear
                                sub_parents.append(n)

                        processed.append(group)
                        parent_nodes.append(sub_parents)
                    else:
                        # Process single node
                        n = nodes
                        if (
                            input_type in ("node", "node_like")
                            or self.params[input_key]["status"] == "ult_input"
                        ):
                            processed.append(n)
                        else:
                            processed.append(
                                utils.get_nested_value(n, input_source_field)
                            )

                        if validate_type(n, "node"):
                            parent_nodes.append(n)

                input_key_data[input_key] = {
                    "parent_nodes": parent_nodes,
                    "nodes": processed,
                    "dim": input_dim,
                }

                # Update count_dims
                if input_dim != -1:
                    count_dims[input_dim] = count_dims.get(input_dim, 0) + 1

            # the following has format: [({'x': [1, 2], 'y': 3, 'z': 10,}, ['px1', 'px2']), ...]
            params_with_parent_list = create_params_list(input_key_data)

            # --------------------------------------------------------------------
            """ run self.cp_run_func and generate list_result """

            output_info = {}  # output_schema there is only one element in it
            for output_key, output_info in output_schema.items():
                output_info.setdefault("type", Any)
                output_info.setdefault("name", "output")

            list_result = []
            for (
                input_func_args,
                parent_nodes,
            ) in params_with_parent_list:  # zip(params_list, parent_nodes_list):
                func_args = raw_params.copy()
                func_args.update(input_func_args)

                func_results = self.cp_run_func(**func_args)
                if step_type in ("node_to_node", "list_to_node"):
                    list_result.append(
                        {
                            "parent_nodes": parent_nodes,  # new_node_parents,
                            "func_result": func_results,
                        },
                    )
                elif step_type in ("node_to_list", "list_to_list"):
                    for func_result in func_results:
                        list_result.append(
                            {
                                "parent_nodes": parent_nodes,  # new_node_parents,
                                "func_result": func_result,
                            }
                        )

            # --------------------------------------------------------------------
            """
            Process function results and create new nodes.

            Args:
            list_result (list): List of dictionaries containing parent nodes and function results.
            output_info (dict): Additional information for node creation.
            output_format (str): Format of the output ('node_like', 'node', 'graph', 'dict', 'none', or other).

            Returns:
            list: List of newly created nodes.

            Creates nodes based on function results and output format. Handles various formats differently:
            - 'node_like' or 'node': Creates nodes with content and extra information.
            - 'graph': Combines result graph with existing graph and adds new nodes.
            - 'dict': Creates nodes for each key-value pair in the result.
            - 'none': Skips node creation.
            - Other formats: Creates a single node with the result as content.

            Updates self.nodes with new nodes.
            """
            new_nodes = []

            for d in list_result:
                parent_nodes = d["parent_nodes"]
                result = d["func_result"]

                # Create a new dictionary that prioritizes result keys over output_info keys
                node_params = output_info.copy()

                if output_format in ("node_like", "node"):
                    for key, value in result.items():
                        if key not in ["content", "extra"]:
                            node_params[key] = value

                    node_content = result.get("content")
                    node_extra = result.get("extra", {})
                    new_node = self.node_graph.add_node(
                        content=node_content,
                        **node_params,
                        # **output_info,
                        extra=node_extra,
                        parent_nodes=parent_nodes,
                        step_id=self.step_id,
                        step_name=self.full_name,
                        cp_name=self.cp_name,
                        # bp_name=self.bp_name,
                    )
                    new_nodes.append(new_node)
                elif output_format == "graph":
                    # Add missing information to nodes in the result graph
                    for _, data in result.nodes(data=True):
                        if not data.get("step_id", False):
                            data["step_id"] = self.step_id
                        if not data.get("step_name", False):
                            data["step_name"] = self.full_name
                        if not data.get("cp_name", False):
                            data["cp_name"] = self.cp_name

                    existing_nodes = set(self.node_graph.nodes())

                    self.node_graph.combine_graph(result)
                    for key, node in self.node_graph.nodes(data=True):
                        if key not in existing_nodes:
                            new_nodes.append(node)

                elif output_format == "dict":
                    for k, v in result.items():
                        new_node = self.node_graph.add_node(
                            content=v,
                            step_id=self.step_id,
                            step_name=self.full_name,
                            cp_name=self.cp_name,
                            # bp_name=self.bp_name,
                            **{k2: v2 for k2, v2 in output_info.items() if k2 == k},
                            parent_nodes=parent_nodes,
                        )
                        new_nodes.append(new_node)
                elif output_format == "none":
                    pass
                elif output_format != "node":
                    new_node = self.node_graph.add_node(
                        content=result,
                        step_id=self.step_id,
                        step_name=self.full_name,
                        cp_name=self.cp_name,
                        # bp_name=self.bp_name,
                        **output_info,
                        parent_nodes=parent_nodes,
                    )
                    new_nodes.append(new_node)

                else:
                    new_nodes.append(result)

            self.nodes = new_nodes

            return new_nodes

        # except Exception as e: TODO: later will add this block back
        #     node_ids_after = set(self.node_graph.nodes())
        #     created_node_ids = node_ids_after - node_ids_before
        #     if self.if_err_remove_node:
        #         for node_id in created_node_ids:
        #             self.context["trash"].append(self.node_graph.nodes[node_id])
        #             self.node_graph.remove_node(node_id)
        #     self._handle_errors(e)

    def get_cache_key(self, key):
        """
        Generate a cache key for the given parameter key.

        Args:
            key (str): The parameter key from the cache schema.

        Returns:
            The generated cache key.

        Process:
        1. Get the cache key from the schema or use the input key.
        2. If the key is in brackets [..], evaluate it as a nested attribute.
        3. Apply a transformer function if specified in the schema.

        Examples:
        - Basic key: "param" -> "param"
        - Nested attribute: "[self.unique_id]" -> value of self.unique_id
        - With transformer: "key" -> transformer(key)
        """
        schema = self.cache_schema.get(key, {})
        cache_key = schema.get("key", key)

        # Handle the case where cache_key is in brackets (needs to be evaluated)
        if re.match(r"^\[.*\]$", cache_key):
            attr_path = cache_key[1:-1]  # Remove brackets
            cache_key = utils.get_nested_value(self, attr_path)

        # Apply transformer if it exists
        if "transformer" in schema:
            cache_key = schema["transformer"](cache_key)

        return cache_key

    def _handle_cache(self):
        """
        Handle caching of parameters based on the cache schema.

        This method is used in self.cp_run_func to update params in self.run.
        It processes each parameter according to the cache schema, initializing
        and retrieving values from the cache as necessary.

        Returns:
            dict: A dictionary of cached parameters.

        Example:
            self.cache_schema = {
                "a": {"key":"yyy", initializer": init_a},
                "<SELF>" : {"key": xxx,
                            "initializer": init_b},
            }

        Parameter Types:
        ----------------
        1. "a" is the param key, "yyy" is the cache key to grab the value in cache
        2. Special "<SELF>" parameter

        Handling Regular Parameters:
        ----------------------------
        For parameters a:
        1. Check if the parameter is in the cache.
        2. If not in cache:
        - Use the initializer function to create the value.
        - Store the value in the self.cache.
        3. Update the parameter with the cached value.

        Handling "<SELF>" Parameter:
        ----------------------------
        1. If its cache_key is found in cache, it's used directly as the "cp"(the cp used) and plug in self.cp_run_func

        """
        cache_params = {}

        if "<SELF>" in self.cache_schema:
            # this is a special token saying that cp used should taken from cache rather than cloning
            cache_key = self.get_cache_key(key="<SELF>")
            cp = self.cache.get(cache_key)
            if cp is not None:
                cache_params["cp"] = cp

        # special treatment for <SELF>
        for key, param in self.params.items():
            if param["status"] != "cache" or param["value"] != "<CACHE>":
                continue

            if key not in self.cache_schema:
                raise KeyError(f"Cache schema not found for key: {key}")

            schema = self.cache_schema[key]
            cache_key = self.get_cache_key(key=key)

            # Check if the key exists in the cache
            if cache_key not in self.cache:
                # If not in cache, use initializer to create it
                if "initializer" in schema:
                    # Inspect the initializer's parameters
                    import inspect

                    init_params = inspect.signature(schema["initializer"]).parameters

                    # Prepare arguments for the initializer
                    args = {}
                    for param_name in init_params:
                        if param_name in self.params:
                            args[param_name] = self.params[param_name]["value"]
                        elif param_name in self.cache:
                            args[param_name] = self.cache[param_name]
                        else:
                            raise ValueError(
                                f"Cannot find value for parameter: {param_name}"
                            )

                    # Initialize and store in cache
                    self.cache[cache_key] = schema["initializer"](**args)
                else:
                    raise ValueError(f"No initializer found for cache key: {cache_key}")

            # Update the param value with the cached value
            cache_params[key] = self.cache[cache_key]
        return cache_params

    # TODO: the following is added later, after most of the things finished
    # def _handle_errors(self, e):
    #     exc_type, exc_value, exc_traceback = sys.exc_info()
    #     tb = exc_traceback
    #     while tb.tb_next:
    #         tb = tb.tb_next
    #     local_vars = tb.tb_frame.f_locals
    #     local_vars.pop("args", None)
    #     local_vars.pop("kwargs", None)
    #     local_vars.pop("self", None)
    #     self.context["error_locals"] = local_vars
    #     logger.debug("Error occurs: %s", local_vars)
    #     backup_path = self.global_config["TEST_OUTPUT_FOLDER_PATH"]
    #     if backup_path is not False:
    #         self._save(backup_path, mode="essential")
    #     raise e

    def __repr__(self):
        return f"<{self.__class__.__name__}(full_name={self.full_name}, name={self.name}), uuid = {self.uuid}>"

    # ----------------------------------------------------------------------------------
    # TODO: the following are useless, consider delete them later if they are still useless

    def reset_status(self):
        """
        currently useless
        Reset the step's status, step_id, output, and nodes to their default values.
        """
        self.status = "queued"
        self.lid = None
        self.output = None
        self.nodes = None

    def get_name(self):
        """resemble Closure method"""
        self.name = f"{self.cp_or_pp.name}:sp{self.lid}"
        return self.name

    def get_full_name(self):
        """resemble Closure method"""
        self.full_name = f"{self.cp_or_pp.full_name}:sp{self.lid}"
        return self.full_name

    def refresh_full_name(self):
        """resemble Closure method"""
        self.get_name()
        self.get_full_name()

    def params_check(self):
        """exactly same as Component method"""
        for k, v in self.params.items():
            if v["status"] == "empty":
                return False
        return True

    def set_attr(self, kwargs):
        """useless now. similar function as in Component"""
        for key, value in kwargs.items():
            if key in self.params_key:
                self.params[key] = value
            else:
                setattr(self, key, value)
