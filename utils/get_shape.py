import json

import numpy as np


def get_shape(item):
    """
    Recursively determines the shape of an item without loading
    all data into memory (lazy evaluation).
    """
    if item is None:
        return ()

    # 1. Handle NumPy Arrays directly (Fastest)
    if isinstance(item, np.ndarray):
        return item.shape

    # 2. Handle Complex Dictionaries (Treat as Scalar)
    # If it is a dictionary representing a complex number, it has no dimension (scalar).
    if isinstance(item, dict):
        if 'real' in item and 'imag' in item:
            return ()
            # If it's a generic dict (not complex), we usually treat it as a scalar object
        # or you might want to count keys. Assuming scalar for this context:
        return ()

    # 3. Handle Strings (Try JSON)
    if isinstance(item, str):
        try:
            # We parse to see if it holds a list structure
            loaded = json.loads(item)
            return get_shape(loaded)
        except (ValueError, json.JSONDecodeError):
            # It's just a regular string -> Scalar
            return ()

    # 4. Handle Lists and Tuples (The Recursive Part)
    if isinstance(item, (list, tuple)):
        if len(item) == 0:
            return (0,)

        # We assume the list is rectangular (homogeneous).
        # We peek at the first element to determine the inner shape.
        inner_shape = get_shape(item[0])

        # Combine current length with inner shape
        return (len(item),) + inner_shape

    # 4b. Handle other sequence-like types (range, custom list-like, etc.)
    if hasattr(item, '__len__') and hasattr(item, '__getitem__') and not isinstance(item, str):
        if len(item) == 0:
            return (0,)
        inner_shape = get_shape(item[0])
        return (len(item),) + inner_shape

    # 5. Handle Scalars (int, float, complex, np.number)
    if isinstance(item, (int, float, complex, np.number)):
        return ()

    # Fallback for unknown objects
    return ()


def extract_complex(item, out):
    # Handle None / missing values (treat as 0)
    if item is None:
        out.append(0.0)
        return

    # Blatt: komplexes Dict
    if isinstance(item, dict) and 'real' in item and 'imag' in item:
        out.append(complex(item['real'], item['imag']))
        #val_idx_item.append(0)
        return

    # Blatt: Skalar
    elif isinstance(item, (int, float, complex, np.number)):
        out.append(complex(item))
        #val_idx_item.append(0)
        return

    # Ast: Liste / Tuple / Array
    elif isinstance(item, (list, tuple, np.ndarray)):
        for sub in item:
            extract_complex(
                sub,
                out,
                #val_idx_item,
            )
        return

    elif isinstance(item, str):
        extract_complex(json.loads(item), out)
        return
    else:
        try:
            float(item)
            out.append(complex(item))
            #val_idx_item.append(0)
            return
        except Exception as e:
            print("UNKNOWN extraction item", item, type(item), e)


"""
def vals_to_sorted_complex_array(vals):
    
    return arr[np.argsort(np.abs(arr))]  # Sortierung nach Betrag
"""
