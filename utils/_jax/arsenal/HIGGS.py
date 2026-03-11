
import jax.numpy as jnp
from jax import jit, vmap



@jit
def calc_lambda_H(_mass: jnp.ndarray, vev: jnp.ndarray) -> jnp.ndarray:
    # λ_H = m^2 / (2 v^2)
    lambda_H = (_mass ** 2) / (2.0 * vev ** 2)
    return lambda_H


@jit
def calc_dV_dh(
        vev: jnp.ndarray,
        lambda_H: jnp.ndarray,
        h: jnp.ndarray
) -> jnp.ndarray:
    # μ = v * sqrt(λ) higgs_potential_derivative
    mu = vev * jnp.sqrt(lambda_H)
    dV_dh = -mu ** 2 * (vev + h) + lambda_H * (vev + h) ** 3
    return dV_dh




@jit
def calc_laplacian_h(
    h: jnp.ndarray,
    p_axes, m_axes,
    d,
    dt,
    # neighbor_pm_val_same_type:list[list, list],

) -> jnp.ndarray:


    @jit
    def _d_spatial(field_forward, field_backward, d_space):
        return (field_forward - field_backward) / (2.0 * d)


    #def _wrapper(val_plus, val_minus, h):
    def _wrapper(dir_p, dir_m, h, d):
        np = jnp.roll(h, shift=dir_p, axis=(0, 1, 2, 3))
        nm = jnp.roll(h, shift=dir_m, axis=(0, 1, 2, 3))

        #lh = (val_plus + val_minus - 2.0 * h) / (d_array ** 2)
        # Die Berechnung wird Array-weise durchgeführt.
        calc_result = _d_spatial(
            field_forward=np,
            field_backward=nm,
            d_space=d
        )
        return calc_result

    result = vmap(_wrapper, in_axes=(
        0,
        0,
        None,
        None,
        None,
    ))(
        p_axes,
        m_axes,
        h,
        d,
        dt,
    )

    laplacian_h = jnp.sum(result)
    return laplacian_h



@jit
def calc_dmu_h(
        h,  # Aktuelles Gitter (Psi(t))
        prev_h,  # Gitter des vorherigen Zeitschritts (Psi(t-dt))
        d,  # Räumlicher Gitterabstand d
        dt,  # Zeitschrittweite
        p_axes, m_axes
):

    # 1. Funktion für die räumliche Zentraldifferenz
    @jit
    def _d_spatial(field_forward, field_backward, d_space):
        return (field_forward - field_backward) / (2.0 * d_space)

    # 2. Funktion für die zeitliche Ableitung (Backward Difference)
    def _d_time(field_current, field_prev, d_time):
        return (field_current - field_prev) / d_time

    # --- Räumliche Ableitungen (Batch-Verarbeitung der 13 Paare) ---

    def _calc_spatial_derivative(dir_p, dir_m):
        # np und nm sind die VOLLSTÄNDIGEN verschobenen Gitter-Arrays
        np = jnp.roll(h, shift=dir_p, axis=(0, 1, 2, 3))
        nm = jnp.roll(h, shift=dir_m, axis=(0, 1, 2, 3))

        # Die Berechnung wird Array-weise durchgeführt.
        calc_result = _d_spatial(
            field_forward=np,
            field_backward=nm,
            d_space=d
        )
        return calc_result

    # VMAP iteriert korrekt über die Listen der Richtungs-Tupel (pm_axes)
    vmapped_func = vmap(
        _calc_spatial_derivative,
        in_axes=(0, 0)
    )

    # JIT-Kompilierung des VMAP-Kerns
    dmu_spatial = vmapped_func(p_axes, m_axes)  # Liefert ein Array von 13 Ableitungs-Arrays

    # --- Zeitliche Ableitung ---
    time_res = _d_time(
        field_current=h,
        field_prev=prev_h,
        d_time=dt
    )

    # Konvertierung des Array-Ergebnisses des vmap-Kerns in eine Liste von Arrays
    dmu_h = list(dmu_spatial)

    # Zeitlichen Term an erster Stelle einfügen
    dmu_h.insert(0, time_res)

    return dmu_h



@jit
def calc_h(
    h: jnp.ndarray,
    _mass: jnp.ndarray,
    prev_h: jnp.ndarray,
    laplacian_h: jnp.ndarray,
    dV_dh: jnp.ndarray,
    dt: jnp.ndarray
  ) -> jnp.ndarray:

    def _mass_term(h: jnp.ndarray, _mass: jnp.ndarray) -> jnp.ndarray:
        return - (_mass ** 2) * h

    mass_term = _mass_term(h, _mass)
    dt2 = jnp.asarray(dt) ** 2
    h = 2.0 * h - prev_h + dt2 * (laplacian_h + mass_term - dV_dh)
    return h

@jit
def calc_phi(h: jnp.ndarray, vev: jnp.ndarray) -> jnp.ndarray:
    # returns 2-component phi as in original: [0, (vev + h)/sqrt(2)]
    sqrt2 = jnp.sqrt(2.0)
    phi = jnp.stack([0.0, (vev + h) / sqrt2])
    return phi

@jit
def calc_energy_density(
    dmu_h: jnp.ndarray,
    _mass: jnp.ndarray,
    h: jnp.ndarray,
    vev: jnp.ndarray,
    laplacian_h: jnp.ndarray
) -> jnp.ndarray:

    def _higgs_potential(_mass: jnp.ndarray, h: jnp.ndarray, vev: jnp.ndarray, laplacian_h: jnp.ndarray) -> jnp.ndarray:
        m2 = _mass ** 2
        # note: original code used laplacian_h factors in higher terms; keep same structure
        return 0.5 * m2 * h ** 2 + laplacian_h * vev * h ** 3 + 0.25 * laplacian_h * h ** 4

    kinetic = 0.5 * (dmu_h[0] ** 2)
    gradient = 0.5 * jnp.sum(dmu_h[1:] ** 2)
    potential = _higgs_potential(_mass, h, vev, laplacian_h)
    energy_density = kinetic + gradient + potential
    return energy_density
