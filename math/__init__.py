import itertools

def apply_all_operator_combinations(variables):
    results = {}

    keys = list(variables.keys())
    combos = itertools.combinations(keys, 2)
    op_patterns = list(OPS.items())

    for (a, b) in combos:
        for symbol, func in op_patterns:
            name = f"{a}{symbol}{b}"
            try:
                res = func(variables[a], variables[b])
                results[name] = res
            except Exception as e:
                results[name] = f"Error: {e}"

    return results

# Beispiel: Matrix und Skalarwerte
r"""x = {
    'a': np.array([[1, 2], [3, 4]]),
    'b': np.array([[2, 0], [1, 2]]),
    'c': 5
}

results = apply_all_operator_combinations(x)

# Ausgabe (nur ein paar Ergebnisse)
for k, v in list(results.items())[:10]:
    print(f"{k}:\n{v}\n")
"""



