def get_nested_value(obj, key):
    """Retrieve value from nested dictionary or object using dot notation."""
    keys = key.split(".")
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            obj = getattr(obj, k, None)
        if obj is None:
            return None
    return obj
