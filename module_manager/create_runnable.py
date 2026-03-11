import jax
import jax.numpy as jnp

LIBS={
    "jax": jax,
    "vmap": jax.vmap,
    "jnp": jnp,
    "jit": jax.jit,
}

def create_runnable(eq_code):
    try:
        namespace = {}

        # Wir fügen die LIBS direkt in den globalen Scope des exec ein
        exec(eq_code, LIBS, namespace)

        # Filtere alle Funktionen heraus
        callables = {
            k: v for k, v in namespace.items()
            if callable(v) and not k.startswith("__")
        }

        if not callables:
            raise ValueError("Keine Funktion im eq_code gefunden.")

        func_name = list(callables.keys())[-1]
        func = callables[func_name]
        return func
    except Exception as e:
        print(f"Err create_runnable: {e}")
        raise e

