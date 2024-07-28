# -*- coding: utf-8 -*-
from gpt_graph.core.graph import Graph
from gpt_graph.core.component import Component
from gpt_graph.utils.load_env import load_env
from gpt_graph.core.components.input_initializer import InputInitializer

from gpt_graph.core.step_graph import StepGraph
from gpt_graph.core.group import Group

from typing import Any
import re
from gpt_graph.utils.priority_queue import PriorityQueue


class Pipeline(Component):
    """
    inherit from Closure ->
    self.get_contains_graph/register
    """

    step_type = "node_to_list"

    def __init__(
        self,
        if_input_initialize=True,
        contain_lvl=0,
        clone_lvl=0,
        **kwargs,
    ) -> None:
        """
        Inherited from Closure:
            base_name, namespace, name, full_name, uuid, contains, contains_lvl, contains_graph,
            rel_graph, contained, all_cps, all_params, config, if_load_env, placeholders

        Inherited from Component:
            lid, prototype, category, if_pp, clones_lvl, clones, global_config, steps, config_keys,
            step_type, cache_schema, output_schema, output_format, bindings, linkings, binding_step_names,
            linking_group, appended_actions, if_auto_detect_input, params, input_schema, node_graph, step_graph, if_dynamic, cache

        WARNING: be careful about assigning Component() to self attributes in __init__
                unless you are sure you are triggering __post_init__ in Closure
        """

        super().__init__(
            func=None,
            node_graph=None,
            contain_lvl=contain_lvl,
            clone_lvl=clone_lvl,
            **kwargs,
        )

        self.cp_roots = []
        self.cp_leaves = []
        self.cp_cursor = None

        self.cache = {}
        self.sub_steps = {}  # all created steps
        self.sub_steps_q = PriorityQueue()  # step call queue
        self.sub_steps_history = []  # historical steps
        # self.dynamic_cps = {}

        self.sub_node_graph = Graph()
        self.sub_step_graph = StepGraph()
        # self.sub_cp_graph = StepGraph()

        self.all_cps = {}  # pure checking purposes from func get_all_cps
        # self.groups = {}
        # self.markers = {}
        # self.pending_actions = []  # only used in connect method, handle p | [p,p] | p
        # self.prepend_actions = []  # vs pending actiobs

        self.lid_counters = {}  # Add this line
        self.method_steps = []

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "if_step"):
                self.method_steps.append(attr)

        if if_input_initialize:
            cp = InputInitializer()
            # the following may return a diff cp
            self.connect(
                cp_or_pp=cp,
                if_inplace=True,
                if_clone_cp=False,
            )
            self.cp_roots = [self.contains[-1]]

            self.input_schema = {"input_data": {"type": Any}}
            self.params = {}

            for param_name, param_info in self.input_schema.items():
                self.params[param_name] = {
                    "type": "input",
                    "status": "input",
                    "value": "<INPUT>",
                    "priority": 0,
                }

    def create_sub_step(
        self,
        cp,
        params={},
        priority=0,
        if_ult_input=False,
        parent_step_names=None,
    ):
        """
        Creates a new sub-step from a component and adds it to the step graph.

        Args:
            cp: Component to create step from.
            params: Dictionary of parameters for the step.
            priority: Priority for the step in the queue.
            if_ult_input: Flag for ultimate input.
            parent_step_names: List of parent step names. If None, uses all leaf nodes.
                Curr only have checking purpose, looking to change in the future

        Returns:
            The newly created step.

        Side effects:
            - Adds step to sub_step_graph, sub_steps_q, and sub_steps dictionary.
        """

        if parent_step_names is None:
            parent_step_names = [
                n["name"] for n in self.sub_step_graph.get_leaf_nodes()
            ]

        # create_step is inherited from Component
        step = cp.create_step(
            params=params,
            if_ult_input=if_ult_input,
            parent_ids=parent_step_names,  # checking purpose in curr settings
            gid=len(self.sub_steps_history),
        )

        self.sub_step_graph.add_node(
            node_id=step.full_name,
            step_id=None,
            name=step.full_name,
            content=step,
            parent_nodes=parent_step_names,
        )
        self.sub_steps_q.push(priority, step)
        self.sub_steps[step.full_name] = step
        return step

    def route_to(self, step_name, params=None):
        """
        Routes to a specific step or multiple steps, creating sub-steps as needed.

        Args:
            step_name (str or list): Name(s) of the step(s) to route to.
            params (dict, optional): Parameters to pass to the created sub-step. Defaults to {}.

        Behavior:
        - If step_name is a list, recursively calls route_to for each step.
        - For a single step, searches for a matching component in self.contains.
        - If a matching Component is found, creates a sub-step with higher priority.

        Raises:
            Exception: If a matching item is found but is not a Component.

        Note:
        - Uses regex for flexible step name matching.
        - Created sub-steps have a priority of 1 (higher than automatic bindings).
        """
        if params is None:
            params = {}

        if isinstance(step_name, list):
            for single_step in step_name:
                self.route_to(single_step, params)
        else:
            target_step = None

            for item in self.contains:
                if re.search(r"\b" + re.escape(step_name) + r"\b", item.full_name):
                    target_step = item
                    if isinstance(target_step, Component):
                        self.create_sub_step(
                            cp=target_step,
                            params=params,
                            priority=1,  # higher priority than automatic bindings. For steps with same priority FIFO
                        )
                    else:
                        raise

    def run(
        self,
        params={},
        params_file=None,
        **kwargs,
    ):
        """
        Args:
            params (dict): Parameters to set for the component. Default is {}.
            params_file (str): Path to a file containing parameters. Default is None, then params_file is the one indicated in config.toml
            kwargs: Additional keyword arguments passed to the first step.

        Process:
        1. Loads and sets parameters.
        2. Initializes step-related structures (queues, graphs, history).
        3. Creates initial steps from root components.
        4. Iteratively executes steps from the queue:
        - Runs each step with appropriate parameters.
        - Updates step graph and history.
        - Checks for and creates new steps based on bindings and linkings.

        Returns:
            list: Output content from the final step.
        """
        print(f"running: {self.name}")

        self.load_params(params_file=params_file)  # using Closure method
        params["self"] = self
        self.set_params(params)

        for cp in self.contains:
            if not cp.params_check():
                raise

        # initialize steps
        self.sub_steps = {}  # all created steps
        self.sub_steps_q.initialize()
        self.sub_steps_history = []
        self.sub_node_graph.initialize()
        self.sub_step_graph.initialize()
        # self.sub_cp_graph.initialize()

        # cp_roots are just InputInitializer set in __init__
        for cp in self.cp_roots:
            self.create_sub_step(
                cp=cp,
                if_ult_input=True,
                priority=0,
                parent_step_names=[],
            )

        # Execute each step in the steps q
        self.curr_step_id = 0
        while self.sub_steps_q:
            _, step = self.sub_steps_q.pop()

            # update step graph for step_id
            self.sub_step_graph.nodes[step.full_name]["step_id"] = self.curr_step_id

            step_params = {
                k: v["value"] for k, v in step.params.items() if v["status"] != "input"
            }  # status is ult_input is allowed

            if not self.sub_steps_history:  # Check if it's the first step
                step_params.update(kwargs)
                step.run(step_id=self.curr_step_id, params=step_params)
            else:
                prev_steps = []
                step.run(
                    parent_steps=prev_steps,
                    step_id=self.curr_step_id,
                    params=step_params,
                )

            self.curr_step_id += 1
            self.sub_steps_history.append(step)

            # Check for new steps created by linkings
            previous_step = self.sub_steps_history[-1]
            prev_cp = previous_step.cp_or_pp
            for cp in self.contains:
                if prev_cp.if_trigger_linkings(next_cp=cp):
                    self.route_to(step_name=cp.full_name)

            # Check for new steps created by bindings
            for component in self.contains:
                if component.if_trigger_bindings(previous_step=previous_step):
                    new_step = self.create_sub_step(
                        cp=component,
                        params={},
                        priority=0,
                        parent_step_names=[previous_step.full_name],
                    )

        last_step = self.sub_steps_history[-1]
        result = [n["content"] for n in last_step.nodes if n["if_output"]]
        return result

    # def initialize_steps(self):
    #     self.steps = {}
    #     self.sub_steps = {}  # all created steps
    #     self.sub_steps_q = []  # step call stack
    #     self.sub_steps_history = []  # historical step

    def clone(self, memo=None, if_assign_prototype=True, context={}):  # optional dict
        """override Component"""
        not_copy_keys = [
            # "base_name",
            # "name",
            # "session",
            # "uuid",
            "clones",  # clones's clone should be empty
            "prototype",
            "contained",  # if contained's id is recorded in memo, then use it, otherwise dont copy
            "all_cps",
            "steps",
            "sub_steps",
            "sub_steps_q",
            "sub_steps_history",
        ]  # uuid will be generated randomly during initialization
        shallow_copy_keys = [
            # "bindings",  # should be deep copied with link
            "global_config",
            "cache",
        ]
        deep_copy_keys = [
            "input_schema",
            "contains",
            "bindings",
            "cp_leaves",
            "cp_cursor",
            "cp_roots",
            "bindings",
            "uuid",
        ]
        link_copy_keys = [
            "node_graph",  # related to nodes
            "step_graph",  # related to steps
            "sub_node_graph",  # pp specific variable
            "sub_step_graph",
        ]

        clone = super().clone(
            memo=memo,
            shallow_copy_keys=shallow_copy_keys,
            not_copy_keys=not_copy_keys,
            deep_copy_keys=deep_copy_keys,
            link_copy_keys=link_copy_keys,
            if_assign_prototype=if_assign_prototype,
        )

        return clone

    def register(self, cp_or_pp, base_name=None):
        """
        Args:
            cp_or_pp: Component or pipeline to register.
            base_name (str, optional): Base name for the item. Defaults to cp_or_pp.base_name.

        Updates self.lid_counters, sets cp_or_pp attributes (contains_lvl, contained, cache),
        renames cp_or_pp, assigns node/step graphs, adds to self.contains, and refreshes full names.

        Note: Overrides closure method. Does not clone cp_or_pp.
        """

        base_name = base_name or cp_or_pp.base_name
        self.lid_counters.setdefault(base_name, -1)
        self.lid_counters[base_name] += 1

        cp_or_pp.contains_lvl = self.contains_lvl + 1
        cp_or_pp.contained = self
        cp_or_pp.set_attr(
            attr_dict={"cache": self.cache},
            if_recursive=True,
        )
        cp_or_pp.rename(
            new_base_name=base_name,
            new_lid=self.lid_counters[base_name],
        )
        cp_or_pp.node_graph = self.sub_node_graph
        cp_or_pp.step_graph = self.sub_step_graph
        self.contains.append(cp_or_pp)
        self.refresh_full_name(if_recursive=True)

    def connect(
        self,
        cp_or_pp,
        mode="node_to_node",
        if_combine=False,
        if_inplace=None,
        if_clone_cp=True,
        if_auto_binding=True,
        if_bindings_complete=True,
    ):
        """
        Connects a component or pipeline to this pipeline, managing graph connections and structure.

        This method:
        1. Connects components or pipelines, either in-place or by creating a new pipeline.
        2. Handles single items or lists of components/pipelines.
        3. Manages cloning, registration, and binding of connected items.
        4. Combines pipelines if specified.

        Args:
            cp_or_pp: Component or pipeline to connect.
            mode (str): Connection mode. Default: "node_to_node".
            if_combine (bool): If True, if cp_or_pp is pp, it will move all its contains under self's contains,
                rather than the pp itself become self's contains. Currently set to False to all situation.
                True is not ready. Default: False.

        Returns:
            None

        Side effects:
            - Modifies the pipeline's internal structure and connections.
        """
        # TODO: judge if if_combine/if_clone_cp is really necessary, as curr False/True all the time

        # if_inplace means that no need to clone self
        if if_inplace is None:
            if self.contained:
                if_inplace = False
            else:
                if_inplace = True

        if if_inplace:
            self_pp = self
        else:
            if if_combine:
                self_pp = self.clone(if_assign_prototype=False)
            else:
                self_pp = Pipeline()
                self_pp.connect(
                    cp_or_pp=self,
                    if_inplace=True,  # inplace as self_pp is just created
                    if_clone_cp=True,  # cloning can solve a lot of issues
                    if_combine=False,
                )

        if isinstance(cp_or_pp, list):
            # handle d | [a,b,c]

            for i, c in enumerate(cp_or_pp):
                self_pp.connect(
                    c,
                    # mode=mode, #TODO: mode seemes useless, may consider delete later
                    if_combine=if_combine,
                    if_inplace=True,
                    if_clone_cp=if_clone_cp,
                    if_auto_binding=False,  # careful here
                )

            if if_auto_binding:
                cloned_cps = self_pp.contains[
                    -len(cp_or_pp) :
                ]  # get newly created cps by prev code
                leaf_uuids = [cp.uuid for cp in self_pp.cp_leaves]

                # TODO: the following logic is not the best, consider change later
                # by setting linkings for [a,b,c] to $if_complete, in self.run, when self.if_trigger_linkings, a Group will groupby the nodes by their name
                # Then nodes with diff names will be sent to diff cp in the [a,b,c]
                for cp_leaf in self_pp.cp_leaves:
                    cp_leaf.linkings = []
                    for cp in cloned_cps:
                        cp_leaf.linkings.append(
                            {
                                "full_name": {"$regex": cp.base_name},
                                "$if_complete": if_bindings_complete,
                            },
                        )

                # update cp_leaves
                self_pp.cp_leaves = [
                    cp for cp in self_pp.cp_leaves if cp.uuid not in leaf_uuids
                ]
                self_pp.cp_leaves.extend(cloned_cps)
            return self_pp

        if if_clone_cp:
            if if_combine:
                # TODO: this part is obsolete, as if_combine is False now, try to consider if it is needed
                context = {
                    "node_graph": self_pp.sub_node_graph,
                    "step_graph": self_pp.sub_step_graph,
                }
            else:
                context = {}
            cp_or_pp = cp_or_pp.clone(context=context)

        if (not cp_or_pp.if_pp) or (cp_or_pp.if_pp and not if_combine):
            self_pp.register(
                cp_or_pp
            )  # define name and lid here, and update self.contains

            if if_auto_binding:
                leaf_uuids = [cp.uuid for cp in self_pp.cp_leaves]

                if len(self_pp.cp_leaves) > 1:
                    cp_or_pp.bindings = [
                        {"cp_or_pp.uuid": {"$eq": cp.uuid}, "$if_complete": True}
                        for cp in self_pp.cp_leaves
                    ]
                else:
                    cp_or_pp.bindings = [
                        {"cp_or_pp.uuid": {"$eq": cp.uuid}} for cp in self_pp.cp_leaves
                    ]

                # update cp_leaves
                self_pp.cp_leaves = [
                    cp for cp in self_pp.cp_leaves if cp.uuid not in leaf_uuids
                ]
                self_pp.cp_leaves.append(cp_or_pp)

        elif cp_or_pp.if_pp and if_combine:
            # TODO: this part is obsolete, as if_combine is False now, try to consider if it is needed
            for i, cp in enumerate(cp_or_pp.contains):
                for key, param in cp.params.items():
                    if param["status"] == "ult_input":
                        cp.params[key]["status"] = "input"

                self_pp.register(cp)

                if if_auto_binding:
                    leaf_uuids = [c.uuid for c in self_pp.cp_leaves]

                    cp.bindings = (
                        {"cp_or_pp.uuid": {"$in": leaf_uuids}} if leaf_uuids else None
                    )
                    self_pp.cp_leaves = [
                        c for c in self_pp.cp_leaves if c.uuid not in leaf_uuids
                    ]
                    self_pp.cp_leaves.append(cp)

        return self_pp

    def save_elements(self, element_type="nodes", filename=None, custom_data=None):
        """override Closure.save_elements"""

        if element_type == "nodes":
            custom_data = {
                "nodes": {
                    node: self.sub_node_graph.nodes[node]
                    for node in self.sub_node_graph.nodes()
                }
            }

        result = super().save_elements(
            element_type=element_type,
            filename=filename,
            custom_data=custom_data,
        )
        return result

    def __or__(self, comp_or_pp):
        """override from Component"""
        return self.connect(
            comp_or_pp,
            if_combine=False,
            if_auto_binding=True,
        )

    def __add__(self, comp_or_pp):
        return self.connect(
            comp_or_pp,
            if_combine=False,
            if_auto_binding=False,
        )

    # def get_sub_cp_graph(self):
    #     """
    #     Create a graph of components (CPs) based on their bindings.
    #     """
    #     self.sub_cp_graph = StepGraph()

    #     def simulate_bindings(bindings, cp):
    #         def process_bindings(bindings):
    #             if isinstance(bindings, str):
    #                 escaped_bindings = re.escape(bindings)
    #                 pattern = f"\\b{escaped_bindings}\\b"
    #                 return {"name": {"$regex": pattern}}
    #             elif isinstance(bindings, list):
    #                 return {"$or": [process_bindings(item) for item in bindings]}
    #             elif isinstance(bindings, dict):
    #                 # Remove 'cp_or_pp.' prefix from keys
    #                 return {
    #                     k.replace("cp_or_pp.", ""): v
    #                     for k, v in bindings.items()
    #                     if k.startswith("cp_or_pp.")
    #                 }
    #             elif bindings is None:
    #                 return None
    #             else:
    #                 raise ValueError(f"Unsupported bindings type: {type(bindings)}")

    #         query = process_bindings(bindings)
    #         if query is None:
    #             return False

    #         # Check if any key doesn't start with 'cp_or_pp.'
    #         if isinstance(bindings, dict) and any(
    #             not k.startswith("cp_or_pp.") for k in bindings.keys()
    #         ):
    #             return False

    #         # Convert cp instance to a dictionary for mql
    #         # cp_dict = cp.__dict__
    #         result = bool(mql([cp], query))  # utils.mql -> mql
    #         return result

    #     # Assign the first CP as the ultimate input CP
    #     ult_input_cp = [
    #         cp for cp in self.contains if cp.bindings is None
    #     ]  # self.contains[0]
    #     for cp in ult_input_cp:
    #         self.sub_cp_graph.add_node(
    #             node_id=cp.full_name,
    #             content=cp,
    #             parent_nodes=[],
    #         )

    #     # Determine parent-child relationships for other CPs
    #     for current_cp in self.contains:
    #         if current_cp.full_name in [cp.full_name for cp in ult_input_cp]:
    #             continue  # Skip the ultimate input CP as it's already added

    #         parent_nodes = []

    #         for other_cp in self.contains:
    #             if other_cp.full_name != current_cp.full_name:
    #                 bindings_result = simulate_bindings(current_cp.bindings, other_cp)
    #                 if bindings_result:
    #                     parent_nodes.append(other_cp.full_name)

    #         if parent_nodes:  # Only add CPs that are linked to others
    #             self.sub_cp_graph.add_node(
    #                 node_id=current_cp.full_name,
    #                 content=current_cp,
    #                 parent_nodes=parent_nodes,
    #             )

    #     # update cp_roots and cp_leaves
    #     # self.cp_roots = [
    #     # cp for cp in self.contains if cp.bindings is None
    #     # ]  # TODO: THIS IS NOT THE CASE LATER IF WE TAKE LINKING INTO ACCOUNT
    #     # TODO: consider LINKING logic
    #     leaf_nodes = self.sub_cp_graph.get_leaf_nodes()
    #     self.cp_leaves = [node["content"] for node in leaf_nodes]

    #     return self.sub_cp_graph
