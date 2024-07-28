import uuid
import weakref


class uuid_ex:
    _instances = weakref.WeakValueDictionary()
    _counter = -1
    _uuid_graph = None

    @classmethod
    def reset(cls, start_value=0):
        cls._counter = start_value
        cls._instances = weakref.WeakValueDictionary()
        cls._uuid_graph = None

    @classmethod
    def show_objects(cls, if_verbose=False):
        from gpt_graph.core.step_graph import StepGraph

        uuid_graph = StepGraph()

        for instance in cls._instances.values():
            nodes = getattr(instance, "nodes", [])
            if (
                nodes
                and isinstance(nodes, list)
                and all(isinstance(elem, dict) for elem in nodes)
            ):
                nodes = [i["content"] for i in nodes]
            else:
                nodes = []

            uuid_graph.add_node(
                node_id=id(instance),
                uuid=str(instance.uuid),
                content=instance,
                name=str(instance.full_name) if hasattr(instance, "full_name") else "",
                level=getattr(instance, "level", 0),
                class_name=instance.__class__.__name__,
                type=instance.__class__.__name__,
                nodes=nodes,
            )

            edge_types = [
                "contains",
                "clones",
                "steps",
                "node_graph",
                "step_graph",
                "sub_node_graph",
                "sub_step_graph",
                # "uuid",
            ]
            for edge_type in edge_types:
                if hasattr(instance, edge_type):
                    if isinstance(getattr(instance, edge_type), list):
                        temp = getattr(instance, edge_type)
                    elif isinstance(getattr(instance, edge_type), dict):
                        temp = getattr(instance, edge_type).values()
                    elif getattr(instance, edge_type) is not None:
                        temp = [getattr(instance, edge_type)]
                    else:
                        temp = []

                    for cp in temp:
                        uuid_graph.graph.add_edge(id(instance), id(cp), type=edge_type)

        uuid_graph.plot(
            if_pyvis=True,
            attr_keys=[
                "node_id",
                "content.full_name",
                "content.base_name",
            ],  # "content.input_schema"],  # Only 'id' is needed
            pyvis_settings={
                "ignored_attr": None,
                "included_attr": None,
                "color_attr": "type",
                "edge_color_attr": "type",
                "label_attr": "name",
            },
        )
        uuid_ex._uuid_graph = uuid_graph

        if if_verbose:
            print(f"Total instances: {len(cls._instances)}")
            for instance in cls._instances.values():
                print(f"UUID: {instance.uuid}")
                if hasattr(instance, "obj"):
                    print(
                        f"Full Name: {getattr(instance,'full_name','<no full name>')}"
                    )
                    print(f"ID: {id(instance)}")
                print("---")

    def __init__(
        self,
        uuid_value=None,
        obj=None,
        mode="counter",
    ):  # counter or uuid mode
        self.mode = mode
        if uuid_value is None:
            self.uuid = self._generate_uuid()
        elif isinstance(uuid_value, (str, int, uuid.UUID, uuid_ex)):
            self.uuid = self._parse_uuid_value(uuid_value)
        else:
            raise ValueError(
                "Invalid uuid_value type. Must be None, str, int, uuid.UUID, or uuid_ex."
            )

        if obj is not None:
            uuid_ex._instances[id(obj)] = obj
            # uuid_ex._instances[id(self)] = self
            # TODO: debug mode vs normal mode, normal mode only record obj info, debug mode record the obj
            # self.obj_info = {
            # "id": id(obj),
            # "class_name": obj.__class__.__name__,
            # "full_name": obj.full_name,
            # }
            # self.obj = obj
            # uuid_ex._instances[id(obj)] = self.obj

    def _generate_uuid(self):
        """Generate a new identifier based on the current mode."""
        if self.mode == "counter":
            uuid_ex._counter += 1
            return uuid_ex._counter
        elif self.mode == "uuid":
            return uuid.uuid4()
        else:
            raise ValueError("Invalid mode. Must be 'uuid' or 'counter'.")

    def _parse_uuid_value(self, uuid_value):
        """Parse the input value based on the mode."""
        if self.mode == "counter" and isinstance(uuid_value, (str, int)):
            return int(uuid_value)
        elif self.mode == "uuid" and isinstance(uuid_value, (str, uuid.UUID)):
            return uuid.UUID(uuid_value) if isinstance(uuid_value, str) else uuid_value
        elif isinstance(uuid_value, uuid_ex):
            return uuid_value.uuid
        else:
            raise ValueError("Invalid uuid_value type for the given mode.")

    def new(self, obj=None):
        """Generate a new identifier based on the current mode and return self."""
        self.uuid = self._generate_uuid()
        if obj is not None:
            # self.obj = obj
            uuid_ex._instances[id(obj)] = obj

        return self

    def __str__(self):
        return str(self.uuid)

    def __repr__(self):
        return f"uuid_ex({self.uuid})"

    # def __eq__(self, other):
    #     if isinstance(other, uuid_ex):
    #         return self.uuid == other.uuid
    #     return False

    def __hash__(self):
        return hash(self.uuid)

    def __eq__(self, other):
        if isinstance(other, uuid_ex):
            return self.uuid == other.uuid
        elif isinstance(other, (int, str, uuid.UUID)):
            return self.uuid == self._parse_uuid_value(other)
        return False


if __name__ == "__main__":
    # Example usage:
    uuid_ex1 = uuid_ex()
    uuid_ex2 = uuid_ex()

    print("UUIDEx1:", uuid_ex1)
    print("UUIDEx2:", uuid_ex2)

    print("Are they equal?", uuid_ex1 == uuid_ex2)

    uuid_ex2.id = (
        uuid_ex1.id
    )  # Manually setting uuid_ex2 to have the same UUID as uuid_ex1

    print("UUIDEx2 after manual change:", uuid_ex2)
    print("Are they equal now?", uuid_ex1 == uuid_ex2)

    uuid_ex1.new()  # Generate a new UUID for uuid_ex1

    print("UUIDEx1 after new UUID:", uuid_ex1)
    print("Are they equal after new UUID?", uuid_ex1 == uuid_ex2)
