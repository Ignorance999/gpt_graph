import os

# import tomli
import tomlkit
import yaml
import json
import gpt_graph.utils.utils as utils
from gpt_graph.core.step_graph import StepGraph
from gpt_graph.utils.uuid_ex import uuid_ex
import re
from gpt_graph.utils.load_env import load_env
import importlib


class Closure:
    def __init_subclass__(cls, **kwargs):
        """
        Automatically adds post-initialization behavior to subclasses.
        Replaces __init__ with a version that calls __post_init__ if it exists.
        """
        super().__init_subclass__(**kwargs)
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            if hasattr(self, "__post_init__"):
                self.__post_init__()

        cls.__init__ = new_init

    def __post_init__(self):
        """
        Automatically called after __init__.
        - Renames the component using the attribute name
        e.g. in __init__: self.x = Component() then in __post_init__: self.x.rename(new_base_name='x')
        """
        from gpt_graph.core.component import Component

        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Component):
                # Perform some action. Here we just print the attribute name and value.
                print(f"Processing {attr_name}: {attr_value.name}")
                attr_value.rename(new_base_name=attr_name)

    def __init__(
        self,
        base_name=None,
        namespace=None,
        if_load_env=False,
    ):
        if base_name:
            self.base_name = base_name
        else:
            self.base_name = self.__class__.__name__

        self.namespace = namespace
        self.name = self.get_name()
        self.full_name = self.get_full_name()

        self.uuid = uuid_ex(obj=self)
        self.contains = []
        self.contains_lvl = 0

        self.contains_graph = None
        self.rel_graph = None
        self.contained = None

        self.all_cps = {}
        self.all_params = {}
        self.config = {}
        self.if_load_env = if_load_env
        self.placeholders = {}

        if self.if_load_env:
            load_env()

    def set_attr(self, attr_dict, if_recursive=True):
        """
        the purpose of this is to set the attr to curr and all contained objs
        used in Pipeline for assigning cache
        """
        # Set the attributes on the current object
        for attr_name, value in attr_dict.items():
            if hasattr(self, attr_name):
                setattr(self, attr_name, value)

        # If not recursive, stop here
        if not if_recursive:
            return

        # Recursively set the attributes on contained objects
        if hasattr(self, "contains"):
            for contained_obj in self.contains:
                if hasattr(contained_obj, "set_attr"):
                    contained_obj.set_attr(attr_dict, if_recursive=True)

    def register(self, cp_or_pp, base_name=None):
        """
        only register the base_name, because the real name is {base_name}.{lid}. And name is a part of full_name: xx;name;xx...
        """
        base_name = base_name or cp_or_pp.base_name  # TODO: there is some problem here

        cp_or_pp.contains_lvl = self.contains_lvl + 1
        cp_or_pp.contained = self

        # rename will set the base_name and refresh full_name recursively
        cp_or_pp.rename(
            new_base_name=base_name,
        )
        self.contains.append(cp_or_pp)
        self.refresh_full_name(if_recursive=True)

    def if_register(self, cp):
        result = id(cp) in [id(c) for c in self.contains]
        return result

    def get_all_cps(self, if_refresh_full_name=True):
        """
        helper function only for checking purposes
        get cps recursively
        """
        if if_refresh_full_name:
            self.refresh_full_name()

        self.all_cps.clear()
        for cp in self.contains:
            self.all_cps[cp.full_name] = cp
            # Recursively collect components from the sub-component
            if cp.if_pp:
                self.all_cps.update(cp.get_all_cps(if_refresh_full_name=False))

        return self.all_cps

    def get_contains_graph(self, graph=None, if_plot=False):
        """
        helper function only for checking purposes
        """
        graph = self.get_rel_graph(
            edge_types=["contains"],
            if_plot=if_plot,
            if_assign=False,
        )
        self.contains_graph = graph
        return graph

    def get_rel_graph(self, graph=None, edge_types=None, if_plot=False, if_assign=True):
        """
        helper function only for checking purposes
        create a step_graph, that includes all the relationships recursively
        contains most of the important attributes of the current obj
        """

        graph = graph or StepGraph()

        if if_assign:
            self.rel_graph = graph

        if edge_types is None:
            edge_types = [
                "contains",
                "clones",
                "steps",
                "node_graph",
                "step_graph",
                "sub_node_graph",
                "sub_step_graph",
            ]

        def add_node_and_edges(obj, graph=graph, edge_types=edge_types):
            content = None
            if getattr(obj, "nodes", False) and obj.__class__.__name__ == "Step":
                content = [n["content"] for n in obj.nodes if "content" in n]

            graph.add_node(
                node_id=id(obj),
                uuid=str(getattr(obj, "uuid", "")),
                content=content,
                name=obj.full_name if hasattr(obj, "full_name") else "",
                parent_nodes=None,
                level=getattr(obj, "contains_lvl", 0),
                class_name=obj.__class__.__name__,
                input_schema=str(getattr(obj, "input_schema", "")),
                type=obj.__class__.__name__,
            )

            for edge_type in edge_types:
                if hasattr(obj, edge_type):
                    if isinstance(getattr(obj, edge_type), list):
                        items = getattr(obj, edge_type)
                    elif isinstance(getattr(obj, edge_type), dict):
                        items = getattr(obj, edge_type).values()
                    elif getattr(obj, edge_type) is not None:
                        items = [getattr(obj, edge_type)]
                    else:
                        items = []

                    for item in items:
                        if not graph.graph.has_node(id(item)):
                            add_node_and_edges(item, graph=graph, edge_types=edge_types)
                        if not graph.graph.has_edge(id(obj), id(item)):
                            graph.graph.add_edge(id(obj), id(item), type=edge_type)

        add_node_and_edges(self, graph=graph)

        if if_plot:
            graph.plot(
                if_pyvis=True,
                attr_keys=[
                    "node_id",
                    "uuid",
                    "content.full_name",
                    "content.base_name",
                ],
                pyvis_settings={
                    "ignored_attr": None,
                    "included_attr": None,
                    "color_attr": "type",
                    "edge_color_attr": "type",
                    "label_attr": "name",
                },
            )

        return graph

    def get_name(self):
        """
        will be overrided. mostly used for refreshing names when base_name/lid changes
        """
        self.name = self.base_name
        return self.name

    def get_full_name(self):
        """
        will be overrided. mostly used for refreshing names when base_name/lid changes
        """
        if not self.namespace:
            self.full_name = self.name
        else:
            self.full_name = f"{self.namespace};{self.name}"
        return self.full_name

    def get_all_params(self):
        """
        helper function only for checking purposes. get all the params of all attributes recursively
        """
        all_params = {}
        cps = self.get_all_cps()

        for cp_name, cp in cps.items():
            if hasattr(cp, "params"):
                for param_name, param_value in cp.params.items():
                    all_params[f"{cp_name}:{param_name}"] = param_value

        self.all_params = all_params
        return all_params

    def set_placeholders(self, placeholders):
        """
        placeholders are used in setting params. You can assign a param to a placeholder in form of "[placeholder]".
        You can set placeholder real value here to assign the real value for those params.
        """
        self.placeholders.update(placeholders)

        def recursive_replace(cp, placeholders):
            if hasattr(cp, "params"):
                for param in cp.params.values():
                    if isinstance(param, dict) and param.get("placeholder"):
                        if param["placeholder"] in placeholders:
                            param["value"] = placeholders[param["placeholder"]]

            for c in getattr(cp, "contains", []):
                recursive_replace(c, placeholders)

        recursive_replace(self, placeholders)

    def load_params(
        self,
        params_file=None,
        placeholders_file=None,
        if_verbose=True,
        config_names=None,
    ):
        import re

        def custom_toml_parse(toml_string, is_params=True):
            """
            Parse a TOML string and return a structured representation.

            This function parses a TOML string and returns a list of tuples. Each tuple contains:
            1. A prefix (path to the current item)
            2. A dictionary with a single key-value pair
            3. A boolean indicating if the item is a parameter

            Args:
            toml_string (str): The TOML string to parse
            is_params (bool): If False, surrounds non-bracketed keys with square brackets

            Returns:
            list: A list of tuples (prefix, {key: value}, is_param)
            WARNING: the is_param is not equal to the input is_params

            Notes:
            - Nested structures are flattened into the list
            - '<NONE>' values are converted to None
            - Keys surrounded by square brackets are not considered parameters
            """
            parsed = tomlkit.parse(toml_string)
            result = []

            def process_item(item, current_path):
                if isinstance(item, tomlkit.items.Table):
                    for key, value in item.items():
                        process_item(value, current_path + (key,))
                elif isinstance(item, tomlkit.items.InlineTable):
                    processed_inline = {}
                    for key, value in item.items():
                        if value == "<NONE>":
                            processed_inline[key] = None
                        else:
                            processed_inline[key] = value
                    result.append(
                        (current_path[:-1], {current_path[-1]: processed_inline})
                    )
                else:
                    value = item
                    if value == "<NONE>":
                        value = None
                    result.append((current_path[:-1], {current_path[-1]: value}))

            for key, value in parsed.items():
                process_item(value, (key,))

            final_result = []
            for prefix, item in result:
                for key, value in item.items():
                    if not is_params:  # placeholders
                        if not re.match(r"^\[.*\]$", key):
                            key = f"[{key}]"
                    is_param = not re.match(
                        r"^\[.*\]$", key
                    )  # careful this is is_param not is_params
                    final_result.append((prefix, {key: value}, is_param))

            return final_result

        def get_all_config_names(obj):
            """
            in config file, both using class name or base name can have effect on the obj
            """
            config_names = set()
            if hasattr(obj, "base_name"):
                config_names.add(obj.base_name)
            if hasattr(obj, "__class__"):
                config_names.add(obj.__class__.__name__)
            if hasattr(obj, "contains"):
                for contained_obj in obj.contains:
                    config_names.update(get_all_config_names(contained_obj))
            return config_names

        if config_names is None and params_file is None and placeholders_file is None:
            config_names = list(get_all_config_names(self))

        if isinstance(config_names, list):
            results = []
            for config_name in config_names:
                results.extend(
                    self.load_params(
                        params_file, placeholders_file, if_verbose, config_name
                    )
                )
            return results

        # At this point, config_names is a single string

        gpt_graph_folder = os.environ.get("GPT_GRAPH_FOLDER")
        if gpt_graph_folder is None:
            load_env()
        gpt_graph_folder = os.environ.get("GPT_GRAPH_FOLDER")
        if gpt_graph_folder is None:
            raise

        if params_file is None and placeholders_file is None:
            config_path = os.path.join(gpt_graph_folder, r".\config\config.toml")
            with open(config_path, "rb") as f:
                config = dict(tomlkit.load(f))

            # config.toml have format:
            # [path]
            #    [path.ReadBook]
            #    params = '.\config\pipelines\read_book.toml'

            class_config = config.get("path", {}).get(config_names, {})

            params_files = class_config.get("params", [])
            placeholders_files = class_config.get("placeholders", [])

            # Ensure both are lists
            if isinstance(params_files, str):
                params_files = [params_files]
            if isinstance(placeholders_files, str):
                placeholders_files = [placeholders_files]

            # Combine params and placeholders into a single list of tuples
            files_to_process = [(file, True) for file in params_files] + [
                (file, False) for file in placeholders_files
            ]

            if not files_to_process:
                print(f"No settings file defined for class {config_names}")
                return {}
        else:
            # If params_file or placeholders_file is provided, use them
            files_to_process = []
            if params_file:
                files_to_process.extend(
                    (file, True)
                    for file in (
                        params_file if isinstance(params_file, list) else [params_file]
                    )
                )
            if placeholders_file:
                files_to_process.extend(
                    (file, False)
                    for file in (
                        placeholders_file
                        if isinstance(placeholders_file, list)
                        else [placeholders_file]
                    )
                )

        results = []

        def process_file(file, is_params=True):
            """
            Process a file and return its contents as a structured list.

            This function handles two types of files:
            1. Python (.py) files
            2. TOML files

            For Python files, it imports the file as a module and extracts its variables.
            For TOML files, it loads the content and processes it as a dictionary.

            Parameters:
            file (str): The path to the file to be processed. If not an absolute path,
                        it's assumed to be relative to `gpt_graph_folder`.

            Returns:
            list: A list of tuples, where each tuple contains:
                - A tuple of strings representing the path in the structure
                - A dictionary of parameters or values
            """
            if not os.path.isabs(file):
                file = os.path.join(gpt_graph_folder, file)

            if file.endswith(".py"):
                module_name = os.path.splitext(os.path.basename(file))[0]
                spec = importlib.util.spec_from_file_location(module_name, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                cp_name_tuple = (self.__class__.__name__,)
                params = {
                    name: value
                    for name, value in module.__dict__.items()
                    if not name.startswith("_")
                }
                if not is_params:
                    params = {f"[{k}]": v for k, v in params.items()}
                return [(cp_name_tuple, params, is_params)]

            else:
                with open(file, "rb") as f:
                    toml_data = f.read()
                return custom_toml_parse(toml_data, is_params=is_params)

        for file, is_params in files_to_process:
            results.extend(process_file(file, is_params))

        for cp_name_tuple, params, is_params in results:
            if if_verbose:
                print(
                    f"{'Loading params' if is_params else 'Loading placeholders'}: {'.'.join(cp_name_tuple)}"
                )

            if is_params:
                self._set_params_with_tuple(
                    cp_name_tuple=cp_name_tuple,
                    params=params,
                    base_priority=0,
                )
            else:
                self.set_placeholders(
                    placeholders=params,
                )

        return results

    def set_params(self, raw_params={}, base_priority=1000):
        """
        Set parameters for the object.

        Parameters:
        raw_params (dict): Parameters to set. Key format:
            "a;b;...;n:p" or "p"
            Sets p in the deepest matching path.
        base_priority (int): Priority level. manual change: 1000.

        Examples:
        set_params({
            "a;b:y": 2,
            "a:z": 3,
            "w": 4
        }, 1000)

        Sets:
        - y in a.b (and a.b.d, a.b.e.f, etc. if they exist)
        - z in a (and a.d, a.e.f, etc. if they exist)
        - w at root level

        Note: Matches the longest path possible. Overwrites existing params.
        """

        for key, value in raw_params.items():
            if ":" in key:
                # Case 1 and 2: Key contains ":"
                path_part, param_part = key.split(":", 1)
                if ";" in path_part:
                    # Case 1: Both ":" and ";" present
                    cp_tuple = tuple(path_part.split(";"))
                else:
                    # Case 2: ":" present but no ";"
                    cp_tuple = (path_part,)
                param_key = param_part
            else:
                # Case 3: Neither ":" nor ";" present
                cp_tuple = ()  # empty tuple for default path
                param_key = key
            params = {param_key: value}

            self._set_params_with_tuple(
                cp_name_tuple=cp_tuple,
                params=params,
                base_priority=base_priority,
            )

    def _set_params_with_tuple(
        self,
        cp_name_tuple=[],
        params={},
        base_priority=1000,  # base priority for manual change
        if_verbose=True,
    ):
        """
        Set parameters for components recursively.

        Args:
        cp_name_tuple (list): Path to target component.
        params (dict): Parameters to set.
        base_priority (int): Base priority for changes. Default 1000.
        if_verbose (bool): Print verbose output. Default True.

        Examples:
        self._set_params_with_tuple(
            cp_name_tuple=["a", "b"],
            params={"c": 2, "d": [test]},
            base_priority=1000
        )
        # Sets c and d for a;b. d is set to placeholder [test]. Later can set param [test] = xxx

        Notes:
        - Updates params based on priority
        - Handles caching and placeholders
        - Can update at multiple levels for partial path matches
        """

        def recursive_set_params(
            cp, cp_name_tuple, params, depth_priority, base_priority
        ):
            is_match = False
            if cp_name_tuple:
                target_name = cp_name_tuple[0]
                if "." in target_name:
                    base_name, lid = target_name.split(".", 1)
                    is_match = (
                        cp.__class__.__name__ == base_name
                        or getattr(cp, "base_name", "") == base_name
                    ) and str(getattr(cp, "lid", "")) == lid
                else:
                    is_match = (
                        cp.__class__.__name__ == target_name
                        or getattr(cp, "base_name", "") == target_name
                    )

            # Always multiply by 2 when going down a level
            depth_priority *= 2

            if is_match:
                # Add 1 to depth_priority only if there's a match
                depth_priority += 1
                next_tuple = cp_name_tuple[1:]
            else:
                next_tuple = cp_name_tuple

            # Check if we should update parameters
            if not next_tuple:
                final_priority = base_priority + depth_priority
                for param_name, param_value in params.items():
                    # Special case for updating input schema
                    if param_name == "<UPDATE_INPUT_SCHEMA>":
                        if hasattr(cp, "update_input_schema"):
                            cp.update_input_schema(param_value)
                        if if_verbose:
                            print(f"Updating input schema for {cp.full_name}")
                        continue
                    elif param_name == "<UPDATE_STEP_TYPE>":
                        cp.step_type = param_value
                        if if_verbose:
                            print(f"Updating step type for {cp.full_name}")
                        continue

                    elif hasattr(cp, "params") and param_name in cp.params:
                        param = cp.params[param_name]
                        # Update parameter if new priority is higher
                        if final_priority >= param.get("priority", 0):
                            if if_verbose:
                                print(
                                    f"Setting {cp.full_name}:{param_name} = {param_value}"
                                )
                                print(
                                    f"Reset priority from {param.get('priority', 0)} -> {final_priority}"
                                )

                            # Handle placeholder parameters
                            if isinstance(param_value, str) and re.match(
                                r"^\[.*\]$", param_value
                            ):
                                param["placeholder"] = param_value
                            else:
                                if (
                                    param_value == "<CACHE>"
                                    and param_name in cp.cache_schema
                                ):
                                    param["status"] = "cache"

                                if (
                                    param["value"] == "<CACHE>"
                                    and param_value != "<CACHE>"
                                ):
                                    param["status"] = "assigned"

                                param["value"] = param_value

                            # Resolve placeholders
                            if (
                                param["placeholder"] is not None
                                and param["placeholder"] in self.placeholders
                            ):
                                param["value"] = self.placeholders[param["placeholder"]]
                                param["priority"] = 1000

                            param["priority"] = final_priority
                            param["status"] = "load" if base_priority == 0 else "manual"
                        elif if_verbose:
                            print(
                                f"Params unchanged due to priority {final_priority} is lower than ori {param.get('priority', 0)}"
                            )

            # Recursive call for all contained components
            for c in getattr(cp, "contains", []):
                recursive_set_params(
                    c, next_tuple, params, depth_priority, base_priority
                )

        recursive_set_params(
            cp=self,
            cp_name_tuple=cp_name_tuple,
            params=params,
            depth_priority=0,
            base_priority=base_priority,
        )

    def params_to_toml(self, params=None, output_file_path=None, return_string=False):
        if params is None and hasattr(self, "get_all_params"):
            params = self.get_all_params()
        else:
            print("there is no get_all_params method. create params toml fails")

        if output_file_path is None:
            class_name = getattr(self, "base_name", self.__class__.__name__)
            gpt_graph_folder = os.getenv("GPT_GRAPH_FOLDER")
            output_file_path = os.path.join(
                gpt_graph_folder, rf"./config/{class_name}.toml"
            )

        def process_key(key):
            key = key.replace(";", ".")
            key = re.sub(r"\.\d+$", "", key)
            return key

        def process_value(val):
            if isinstance(val, (str, int, float, bool)):
                return val
            elif val is None:
                return "<NONE>"
            elif isinstance(val, (list, dict)):
                return tomlkit.item(val)
            else:
                return str(val)

        doc = tomlkit.document()

        for key, value in params.items():
            components = key.split(":")

            if len(components) > 1:
                table_components = process_key(components[0]).split(".")
                current_table = doc
                for component in table_components:
                    if component not in current_table:
                        current_table.add(component, tomlkit.table())
                    current_table = current_table[component]
            else:
                current_table = doc

            if value.get("type") == "param":
                final_key = process_key(components[-1])
                final_value = process_value(value.get("value", "<NONE>"))

                if final_key and isinstance(final_key, str):
                    if final_key in current_table:
                        current_table[final_key] = final_value
                    else:
                        current_table.add(final_key, final_value)

        toml_string = tomlkit.dumps(doc)

        if output_file_path and not return_string:
            with open(output_file_path, "w") as f:
                f.write(toml_string)
            return f"TOML content written to {output_file_path}"

        if return_string:
            return toml_string

        raise ValueError(
            "Either output_file_path must be provided or return_string must be True"
        )

    def save_elements(self, element_type, filename=None, custom_data=None):
        """
        Save specified elements to a file in YAML or JSON format.

        Parameters:
        element_type (str): Type of elements to save. Options:
                            "nodes", "steps", "steps_history", "dynamic_steps".
                            Default is "nodes".
        filename (str): Path to save file. If None, uses default path.
                        File extension determines format (.yaml/.yml or .json).
                        Defaults to .yaml if not specified.
        custom_data (dict): if element_type in custom_data.keys, will use custom data instead

        Examples:
        save_elements("nodes", "graph_nodes.yaml")
        save_elements("steps", "workflow_steps.json")

        Notes:
        - For "nodes", saves sub_node_graph data.
        - For other types, saves corresponding attribute data.
        - Data is serialized before saving.
        - Prints confirmation message after saving.
        """
        filename = filename or os.path.join(
            os.environ.get("OUTPUT_FOLDER"), f"temp_save_{element_type}.json"
        )
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            file_type = "yaml"
        elif filename.endswith(".json"):
            file_type = "json"
        else:
            file_type = "yaml"
            filename += ".yaml"
            print("modify save node file ext as .yaml")

        # Get data
        if custom_data and element_type in custom_data:
            data = custom_data[element_type]
        else:
            data = getattr(self, element_type, None)

        data = utils.serialize_json_recursively(data)

        # Writing to a YAML file
        with open(filename, "w", encoding="utf-8") as file:
            if file_type == "yaml":
                yaml.safe_dump(data, file, default_flow_style=False)
            else:
                json.dump(data, file, indent=4)

        print(f"Data successfully saved to {filename}")

    def refresh_full_name(self, namespace=None, if_recursive=True):
        """
        Update the full name of this component and its subcomponents.

        Parameters:
        namespace (str): New namespace for the component. If None, keeps current.
        if_recursive (bool): Whether to refresh subcomponents. Default is True.

        Behavior:
        1. Updates namespace if provided.
        2. Refreshes name and full_name for contained components.
        3. Recursively refreshes all subcomponents with empty namespace.

        Example:
        component.refresh_full_name(namespace="new_namespace")
        # Updates component's namespace and refreshes names of all subcomponents
        """
        if self.contained:
            if namespace is not None:
                self.namespace = namespace
            # refresh name
            self.name = self.get_name()
            self.full_name = self.get_full_name()

        # if it is outside layer, no need to refresh itself
        for cp in self.contains:
            cp.refresh_full_name(namespace="", if_recursive=True)

    def reset_uuid(self, if_recursive=False):
        """
        used in cloning self
        """
        self.uuid.new(obj=self)
        if if_recursive:
            for cp in self.contains:
                cp.reset_uuid()
