import jax.numpy as jnp

def op_add(x, p): return x + p

def op_sub(x, p): return x - p


def op_mul(x, p): return x * p


def op_div(x, p): return x / (p + 1e-6)


def op_pow(x, p): return jnp.power(x, p)


def op_negate(x, p=None): return -x


# --- JAX / Numpy Funktionen ---
def op_dot(x, p):    return jnp.dot(x, p)


def op_matmul(x, p): return jnp.matmul(x, p)


def op_sum(x, p=None): return jnp.sum(x)


def op_mean(x, p=None): return jnp.mean(x)


def op_exp(x, p=None): return jnp.exp(x)


def op_log(x, p=None): return jnp.log(x + 1e-6)


def op_abs(x, p=None): return jnp.abs(x)


def op_sin(x, p=None): return jnp.sin(x)


def op_cos(x, p=None): return jnp.cos(x)


def op_sqrt(x, p=None): return jnp.sqrt(x)

def op_conj(x, p=None): return x.conj()

def op_T(x, p=None): return x.T

def op_assign(x, p=None): return x

def plus_single(x, p=None): return x

OPS_FUNCTIONS = [
    op_add, op_sub, op_mul, op_div, op_pow, op_pow, op_negate, plus_single,
    op_dot, op_matmul, op_matmul, op_sum, op_mean,
    op_exp, op_log, op_abs, op_sqrt, op_sin, op_cos, op_assign
]