from mongoquery import Query
from gpt_graph.utils.get_nested_value import get_nested_value


def mql(documents, query, ignored_keys=None):
    """
    Perform a MongoDB-like query on a list of documents.

    Args:
    documents (list): List of documents(dict) to query.
    query (dict): Query specification.
    ignored_keys (list, optional): Keys to ignore in the query. Defaults to ["$if_complete"].

    Returns:
    list: Filtered and ordered list of documents matching the query.

    The query can include the following special operators:
    - $lambda: Custom filtering function.
    - $order: Custom ordering specification.
      For $order, the value can be an integer or a list of integers:
      - If it's an integer, it selects the nth group after sorting.
      - If it's a list of integers, it selects multiple groups and combines them.

    Example:
    query = {
        "name": {"$regex": "^A"},
        "age": {"$gt": 25, "$order": 0},
        "skills": {"$lambda": lambda x: "Python" in x}
    }
    result = mql(documents, query)
    """

    ignored_keys = ignored_keys or ["$if_complete"]

    def collect_keys(q):
        """Recursively collect all keys from the query."""
        keys = set()
        for key, value in q.items():
            if key.startswith("$"):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            keys.update(collect_keys(item))
            else:
                keys.add(key)
                if isinstance(value, dict):
                    keys.update(collect_keys(value))
        return keys

    def create_nested_dict(doc, keys):
        """Create a nested dictionary for a document based on the collected keys."""
        nested_dict = {}
        for key in keys:
            value = get_nested_value(doc, key)
            parts = key.split(".")
            d = nested_dict
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            d[parts[-1]] = value
        return nested_dict

    # Collect all important keys from the query
    important_keys = collect_keys(query)

    # Extract custom steps if any and clean the query
    custom_steps = {}
    cleaned_query = {}
    for key, value in query.items():
        if isinstance(value, dict):
            cleaned_query[key] = {}
            for sub_key, sub_value in value.items():
                if sub_key in ["$order", "$lambda"] + ignored_keys:
                    custom_steps[sub_key] = custom_steps.get(sub_key, {})
                    custom_steps[sub_key][key] = sub_value
                else:
                    cleaned_query[key][sub_key] = sub_value
        else:
            if key in ["$order", "$lambda"] + ignored_keys:
                # custom_steps[key] = custom_steps.get(key, {})
                custom_steps[key] = value
            else:
                cleaned_query[key] = value

    # Create custom dictionaries for each document
    custom_documents = [
        (create_nested_dict(doc, important_keys), doc) for doc in documents
    ]

    # Apply mongoquery filtering
    q = Query(cleaned_query)
    filtered_nodes = [
        (custom_dict, original_doc)
        for custom_dict, original_doc in custom_documents
        if q.match(custom_dict)
    ]

    # Apply custom steps
    if "$lambda" in custom_steps:
        lambda_steps = custom_steps["$lambda"]
        for key, lambda_func in lambda_steps.items():
            filtered_nodes = [
                (custom_dict, original_doc)
                for custom_dict, original_doc in filtered_nodes
                if lambda_func(get_nested_value(custom_dict, key))
            ]

    if "$order" in custom_steps:
        order_steps = custom_steps["$order"]
        for key, loc in order_steps.items():
            # Group by the specified key
            grouped_nodes = {}  # defaultdict(list)
            for custom_dict, original_doc in filtered_nodes:
                value = get_nested_value(custom_dict, key)
                grouped_nodes.setdefault(value, []).append((custom_dict, original_doc))

            sorted_groups = sorted(grouped_nodes.items())

            if isinstance(loc, str):
                loc = int(loc)

            if isinstance(loc, int):
                loc = [loc]

            if isinstance(loc, list):
                if all(isinstance(item, str) for item in loc):
                    loc = [int(item) for item in loc]

                new_filtered_nodes = []
                for index in loc:
                    if len(sorted_groups) >= max(index, 1):
                        new_filtered_nodes.extend(sorted_groups[index][1])
                    # else:
                    # filtered_nodes = []
                filtered_nodes = new_filtered_nodes
                if not filtered_nodes:
                    break
            else:
                raise ValueError(
                    f"Invalid $order value for key {key}. Expected int or list of ints."
                )

    # Return only the original documents
    result = [original_doc for _, original_doc in filtered_nodes]
    return result


if __name__ == "__main__":
    import pprint
    from gpt_graph.utils.uuid_ex import uuid_ex

    documents = [
        {"name": "Alice", "age": 23, "sex": "M", "uuid": uuid_ex(), "extra": {"t": 4}},
        {"name": "Alice", "age": 23, "sex": "M", "uuid": uuid_ex(), "extra": {"t": 5}},
        {"name": "Alice", "age": 25, "sex": "M", "uuid": uuid_ex(), "extra": {"t": 3}},
        {"name": "Alice", "age": 25, "sex": "F", "extra": {"t": 3}},
        {"name": "Alice", "age": 22, "sex": "F", "extra": {"t": 3}},
        {"name": "Bob", "age": 30, "sex": "M", "extra": {"t": 3}},
        {"name": "Charlie", "age": 35, "sex": "M", "extra": {"t": 3}},
        {"name": "Charlie", "age": 35, "sex": "M", "extra": {"t": 4}},
        {"name": "Diana", "age": 28, "sex": "F", "extra": {"t": 3}},
        {"name": "Eve", "age": 22, "sex": "F", "extra": {"t": 3}},
    ]
    # Sample query with multiple criteria and an embedded $order step

    query = {
        "name": {
            "$in": ["Alice", "Charlie"],
        },
        "age": {
            "$gt": 20,
            "$lt": 40,
            # "$order": -1,  # Custom step to sort by age in descending order
            "$lambda": lambda x: x / 5 == int(x / 5),
            # "$in": [23,25]
        },
        "extra.t": {"$order": [0, 1]},
        # "uuid": {"$eq": uuid_ex(16)},
    }

    # Sample query with $or operator
    # query = {
    #     "$or": [
    #         {
    #             "name": "Alice",
    #             "age": {"$in": [23, 25]},
    #             "sex": "M"
    #         },
    #         {
    #             "name": "Charlie",
    #             "age": {"$gt": 30}
    #         },
    #         {
    #             "name": {"$in": ["Diana", "Eve"]},
    #             "sex": "F",
    #             "age": {"$lt": 30}
    #         }
    #     ],
    #     "extra.t": {"$order": 0}  # This will only apply to documents that have this field
    # }

    # Apply the query with custom steps
    result = mql(documents, query)

    pprint.pprint(result)
    # %%
    # Sample documents
    documents = [
        {
            "_id": 1,
            "name": "Alice",
            "details": {"age": 25, "address": {"city": "New York", "zip": "10001"}},
        },
        {
            "_id": 2,
            "name": "Bob",
            "details": {
                "age": 30,
                "address": {"city": "San Francisco", "zip": "94105"},
            },
        },
        {
            "_id": 3,
            "name": "Charlie",
            "details": {"age": 35, "address": {"city": "New York", "zip": "10002"}},
        },
    ]

    # Define the query
    query = {"details.age": {"$gt": 30}, "details.address.city": "New York"}

    # Apply mongoquery
    q = Query(query)
    filtered_docs = [doc for doc in documents if q.match(doc)]

    print("Filtered documents:", filtered_docs)
