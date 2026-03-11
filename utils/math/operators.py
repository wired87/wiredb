

"""
OPS = {
    # Arithmetik
    '+': op_add,
    '-': op_sub,
    '*': op_mul,
    '/': op_div,
    '**': op_pow,
    '^': op_pow,  # Alias für den Extractor
    'neg': op_negate,
    '+s': plus_single,

    # Lineare Algebra / JNP Spezifisch
    'dot': op_dot,
    'matmul': op_matmul,
    '@': op_matmul,
    'sum': op_sum,
    'mean': op_mean,

    # Mathematische Funktionen
    'exp': op_exp,
    'log': op_log,
    'abs': op_abs,
    'sqrt': op_sqrt,
    'sin': op_sin,
    'cos': op_cos,

    # Zuweisung
    '=': op_assign
}
"""

# Diese Liste ist sicher für JSON und Datenbanken
OPS = [
    '+', '-', '*', '/', '**', '^', 'neg', '+s',
    'dot', 'matmul', '@', 'sum', 'mean',
    'exp', 'log', 'abs', 'sqrt', 'sin', 'cos', '='
]
