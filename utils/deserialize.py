import json


def deserialize(val):
    try:
        if isinstance(val, str):
            val = json.loads(val)
    except Exception as e:
        print(f"Err deserialize: {e}")
    print("deserialized", val, type(val))
    return val
