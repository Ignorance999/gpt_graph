from gpt_graph.utils.uuid_ex import uuid_ex
import copy
from gpt_graph.utils.get_nested_value import get_nested_value


class Group:
    def __init__(
        self,
        nodes=None,
        node_graph=None,
        filter_cri=None,
        group_key=None,
        parent_filter_cri=None,
        parent_group_key=None,
        name=None,
        type=None,
        gid=None,
        if_yield=None,
    ):
        self.uuid = uuid_ex(obj=self)
        self.nodes = nodes
        self.node_graph = node_graph
        self.filter_cri = filter_cri
        self.group_key = group_key
        self.parent_filter_cri = parent_filter_cri
        self.parent_group_key = parent_group_key or "node_id"
        self.name = name or "group"
        self.type = type
        self.gid = gid
        self.contains = {}
        self.clones = []
        self.prototype = None

        self.if_refresh = None
        self.if_yield = if_yield or False
        self._sub_group_index = None

    def initialize(self):
        """
        Set nodes and contains back to original empty state.
        """
        self.nodes = None
        self.contains = {}

    def clone(self, if_copy_nodes=False):
        """
        Create a deep copy of the Group instance, excluding nodes, contains, prototype, and clones
        resembles Component.clone
        """
        deep_copy_keys = [
            "filter_cri",
            "group_key",
            "parent_filter_cri",
            "parent_group_key",
            "name",
            "type",
            "gid",
        ]
        if if_copy_nodes:
            deep_copy_keys.append("nodes")
            self.if_refresh = False

        new_group = Group()

        # Copy all attributes except nodes, contains, prototype, and clones
        for attr, value in vars(self).items():
            if attr in deep_copy_keys:
                setattr(new_group, attr, copy.deepcopy(value))

        # Set the prototype to the original group
        new_group.prototype = self

        # Add the new group to the original group's clones list
        self.clones.append(new_group)

        return new_group

    def reset_uuid(self, if_recursive=False):
        from gpt_graph.core.closure import Closure

        return Closure.reset_uuid(self, if_recursive=if_recursive)

    def run(
        self,
        filter_cri=None,
        group_key=None,  # can both be str or dict[str: func] for grouping criteria
        parent_filter_cri=None,
        parent_group_key=None,
        nodes=None,
        node_graph=None,
        if_refresh=None,
    ):
        """
        Execute the grouping process on nodes based on various criteria.

        Parameters:
        filter_cri (dict, optional): Criteria to filter nodes.
        group_key (str or dict, optional): Key or dictionary of functions to group nodes.
        parent_filter_cri (dict, optional): Criteria to filter parent nodes.
        parent_group_key (str, optional): Key to group parent nodes.
        nodes (list, optional): List of nodes to process. If None, uses filtered nodes.
        node_graph (object, optional): Graph object containing nodes and their relationships.
        if_refresh (bool, optional): Whether to refresh the node list using filter criteria.

        Returns:
        list: List of Group objects representing the grouped nodes.

        This method performs the following steps:
        1. Updates instance attributes if new values are provided.
        2. Filters and groups parent nodes if parent_filter_cri is specified.
        3. Filters child nodes based on filter_cri or uses provided nodes.
        4. Groups child nodes based on their parent groups or directly by group_key.
        5. Further subdivides groups based on the specified group_key.
        6. Creates Group objects for each final group of nodes.

        The grouping can be based on parent-child relationships and/or node attributes.
        It supports both simple key-based grouping and complex grouping using custom functions.

        Raises:
        ValueError: If node_graph is not provided and not set in the instance.
        """
        # Update nodes and node_graph if provided
        if nodes is not None:
            self.nodes = nodes

        if node_graph is not None:
            self.node_graph = node_graph

        if self.node_graph is None:
            raise ValueError("node_graph must be provided")
        self.filter_cri = filter_cri or self.filter_cri

        if parent_filter_cri is not None:
            self.parent_filter_cri = parent_filter_cri

        if group_key is not None:
            self.group_key = group_key

        if parent_group_key is not None:
            self.parent_group_key = parent_group_key

        # Step 1: Filter parent nodes if parent_filter_cri is provided
        parent_groups = {}
        if self.parent_filter_cri:
            parent_nodes = self.node_graph.filter_nodes(self.parent_filter_cri)

            # Step 2: Group parent nodes by group key
            for parent in parent_nodes:
                key_value = get_nested_value(parent, self.parent_group_key)
                if key_value not in parent_groups:
                    parent_groups[key_value] = []
                parent_groups[key_value].append(parent)

        # Step 3: Filter nodes based on filter criteria or use provided nodes
        if if_refresh is None:
            if self.if_refresh is None:
                if_refresh = True
            else:
                if_refresh = self.if_refresh

        self.nodes = (
            self.node_graph.filter_nodes(self.filter_cri) if if_refresh else self.nodes
        )

        # Step 4: Group nodes based on the group of their parent nodes or directly by group key
        if self.parent_filter_cri:
            node_ids = [n["node_id"] for n in self.nodes]

            child_groups = {key: [] for key in parent_groups.keys()}
            for key, parents in parent_groups.items():
                nodes = self.node_graph.filter_nodes(
                    filter_cri={"node_id": {"$in": node_ids}},
                    if_inclusive=True,
                    parents=parents,
                )
                child_groups[key].extend(nodes)
        else:
            child_groups = {"all": self.nodes}

        # Step 5: Further group child nodes based on the group key
        def create_group(nodes, index):
            subgroup_name = f"{self.name}.gp{index}"
            new_group = Group(
                nodes=nodes,
                node_graph=self.node_graph,
                name=subgroup_name,
                type=self.type,
                gid=f"{self.gid}.{index}" if self.gid else str(index),
            )
            return new_group

        final_grouped_nodes = []
        group_index = 0
        for parent_key, nodes in child_groups.items():
            if isinstance(self.group_key, dict):
                subgroups = {}
                for node in nodes:
                    for key, func in self.group_key.items():
                        key_value = func(get_nested_value(node, key))
                        if key_value not in subgroups:
                            subgroups[key_value] = []
                        subgroups[key_value].append(node)
                for subgroup_nodes in subgroups.values():
                    new_group = create_group(subgroup_nodes, group_index)
                    final_grouped_nodes.append(new_group)
                    group_index += 1
            elif self.group_key:
                subgroups = {}
                for node in nodes:
                    key_value = get_nested_value(node, self.group_key)
                    if key_value not in subgroups:
                        subgroups[key_value] = []
                    subgroups[key_value].append(node)
                for subgroup_nodes in subgroups.values():
                    new_group = create_group(subgroup_nodes, group_index)
                    final_grouped_nodes.append(new_group)
                    group_index += 1
            else:
                new_group = create_group(nodes, group_index)
                final_grouped_nodes.append(new_group)
                group_index += 1

        self.contains = final_grouped_nodes
        return self.contains

    def get_nodes(self, if_yield=None):
        """
        used in Step.run to be input to the Step.cp_run_func, if the Group is added in Step.input_schema

        Retrieve nodes from the group.

        Args:
        if_yield (bool, optional): Whether to yield nodes iteratively.
                                Defaults to instance's if_yield value.

        Returns:
        If if_yield is True:
            Single subgroup's nodes or None when exhausted.
        If if_yield is False:
            List of all nodes from all subgroups.

        Runs grouping process if nodes haven't been processed yet.
        """
        if if_yield is None:
            if_yield = self.if_yield

        if self.nodes is None:
            self.run(node_graph=self.node_graph)

        if if_yield:
            if self._sub_group_index is None:
                self._sub_group_index = 0

            if self._sub_group_index < len(self.contains):
                nodes = self.contains[self._sub_group_index].nodes
                self._sub_group_index += 1
                return nodes
            else:
                return None

        else:
            # Non-yield mode: return all nodes every time
            input_key_nodes = [sub_group.nodes for sub_group in self.contains]
            return input_key_nodes
