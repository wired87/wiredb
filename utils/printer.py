import numpy as np

def printer(local_vars: dict, title="🔍 Debug Ausgabe"):
    print(f"\n========== {title} ==========")
    for name, val in local_vars.items():
        if isinstance(val, np.ndarray):
            print(f"{name} np.ndarray, shape={val.shape}, dtype={val.dtype}:\n{val}\n")
        elif isinstance(val, (list, tuple)):
            print(f"{name} {type(val).__name__}, len={len(val)}: {val}")
        elif isinstance(val, dict):
            print(f"{name} dict, len={len(val)}: {val}")
        else:
            print(f"{name} ({type(val).__name__}): {val}")
    print(f"========== Ende {title} ==========\n")
