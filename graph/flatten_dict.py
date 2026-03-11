




def flatten_attributes(attributes):
    """Recursively flattens a nested dictionary, handling lists properly."""
    #print("Flatting attrs", attributes)
    def _flatten(obj, prefix=''):
        flattened = {}

        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}_{k}" if prefix else k
                flattened.update(_flatten(v, new_key))
        elif isinstance(obj, list):
            # Instead of merging into the same dict, preserve the list structure.
            new_items = []
            for item in obj:
                if isinstance(item, dict):
                    # Flatten each list item with an empty prefix so that parent's key isn't repeated.
                    new_items.append(_flatten(item, prefix))
                else:
                    new_items.append(item)
            flattened[prefix] = new_items
        else:
            flattened[prefix] = obj
        return flattened

    return _flatten(attributes)









"""def flatten_attributes(attributes):
    Recursively flattens a nested dictionary, handling lists properly.
    def _flatten(obj, prefix=''):
        flattened = {}

        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}_{k}" if prefix else k
                flattened.update(_flatten(v, new_key))

        elif isinstance(obj, list):
            list_prefix = ""
            for item in obj:
                flattened.update(_flatten(item, list_prefix))
        else:
            flattened[prefix] = obj
        return flattened

    return _flatten(attributes)"""
