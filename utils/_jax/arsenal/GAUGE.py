
import jax

from jax import jit, vmap, lax
import jax.numpy as jnp

@jit
def calc_gg_coupling(
        g_,
        field_value_,
        g,
        field_value,
):

    def _wrapper(
            g_,
            field_value_,
            field_value,
            g,
    ):
        # symmetric effective coupling strength
        g_eff = 0.5 * (g_ + g)

        # simplified antisymmetric field interaction term: [Aμ, Aν]
        j_pair = g_eff * (field_value * field_value_ - field_value_ * field_value)
        return j_pair

    gg_coupling = vmap(
        _wrapper,
        in_axes=(
        0, 0, 0, None, None
    ))(
        g_,
        field_value_,
        field_value,
        g,
    )
    return gg_coupling





@jax.jit
def calc_gf_coupling(
    psi, # psi, psi_bar,psi_bar
    psi_bar,
    field_value,
    g,
    gluon_index=None,
):
    index_map = [
        0, 1, 2, 3
    ]

    def _j_nu_mu(
        psi,
        psi_bar,
        g,
        index,
        o_operator,
        gamma,
        gluon_index=None,
        quark_index=None,
    ):
        def _j_nu_gluon_quark(
            psi,
            psi_bar,
            gamma_mu,
            o_operator,
            g,
            quark_index,
        ):
            j_nu = 0
            # for a in range(3):
            for b in range(3):
                psi_b = psi[b]  # shape: (4,)
                # psi_bar_a = psi_bar[a]  # shape: (4,)
                spinor_scalar = psi_bar @ gamma_mu @ psi_b  # → Skalar
                color_factor = o_operator[quark_index, b]  # → Skalar
                j_nu += spinor_scalar * color_factor
            j_nu *= g
            return j_nu

        def _j_nu_non_qg(
                psi,
                psi_bar,
                gamma_mu,
                o_operator,
                g,
        ):
            j_nu = g * (psi_bar @ gamma_mu @ o_operator @ psi) # take whole psi = correct
            return j_nu

        j_nu = lax.cond(
            gluon_index and quark_index,
            lambda: _j_nu_gluon_quark(
                psi,
                psi_bar,
                gamma[index],
                o_operator,
                g,
                quark_index,
            ),
            lambda: _j_nu_non_qg(
                psi,
                psi_bar,
                gamma[index],
                o_operator,
                g,
            )
        )
        return j_nu * field_value[index]

    vmapped_func = vmap(_j_nu_mu, in_axes=(
        0,
        0,
        None,
        None,
        None,
        None,
    ))(
        psi,
        psi_bar,
        field_value,
        g,
        index=index_map,
        gluon_index=gluon_index,
    )
    gf_coupling = jax.numpy.sum(vmapped_func, axis=0)
    return gf_coupling

@jit
def j_nu(
    gg_coupling,
    gf_coupling
):
    j_nu = jax.numpy.sum(gf_coupling) + jax.numpy.sum(gg_coupling)
    return j_nu


@jit
def calc_field_value(
        dt,
        dmu_fmunu,
        j_nu,
        field_value
):
    """
    ∂_μ F^{μν} = j^ν
    """
    field_value = field_value + dt * (dmu_fmunu - j_nu)
    return field_value



@jit
def calc_fmunu(
    dmuG
):
    """
    Calculates the antisymmetric tensor F from the derivative tensor dmu.

    This is an optimized version using vectorized JAX operations for GPU batch processing.
    It assumes dmu is a JAX array of shape (26, 26) or (26, 26, 1).
    """
    amount_dirs = 13  # As per user request, file originally had 13

    # Squeeze to handle shapes like (26, 26, 1) -> (26, 26)
    # This makes the code robust to whether the input has a trailing dimension of 1
    dmu_s = jnp.squeeze(dmuG)

    # F[mu, nu] = dmu[mu, nu] - dmu[nu, mu]
    # Vectorized implementation for batch processing:
    term1 = dmu_s[:amount_dirs, :4]
    term2 = dmu_s[:4, :amount_dirs].T

    fmunu = term1 - term2
    return fmunu


@jit
def calc_dmuG(
        field_value,  # komplettes grid Aktuelles Gitter
        prev_field_value,  # Gitter des vorherigen Zeitschritts (Psi(t-dt))
        d,  # Räumlicher Gitterabstand d
        dt,  # Zeitschrittweite
        p_axes,
        m_axes,  # ([+dirs], [-dirs])
):
    # 1. Funktion für die räumliche Zentraldifferenz
    def _d_spatial(field_forward, field_backward, d_space):
        """Berechnet (Psi_{i+1} - Psi_{i-1}) / (2.0 * d) für das gesamte Array."""
        return (field_forward - field_backward) / (2.0 * d_space)

    # 2. Funktion für die zeitliche Ableitung (Backward Difference)
    def _d_time(field_current, field_prev, d_time):
        """Berechnet (Psi(t) - Psi(t-dt)) / dt für das gesamte Array."""
        return (field_current - field_prev) / d_time


    def _calc_spatial_derivative(dir_p, dir_m):
        # np und nm sind die VOLLSTÄNDIGEN verschobenen Gitter-Arrays
        np = jnp.roll(field_value, shift=dir_p, axis=(0, 1, 2, 3))
        nm = jnp.roll(field_value, shift=dir_m, axis=(0, 1, 2, 3))

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
        field_current=field_value,
        field_prev=prev_field_value,
        d_time=dt
    )

    # Konvertierung des Array-Ergebnisses des vmap-Kerns in eine Liste von Arrays
    dmuG = list(dmu_spatial)

    # Zeitlichen Term an erster Stelle einfügen
    dmuG.insert(0, time_res)

    return dmuG


@jit
def calc_dmu_fmunu(
        fmunu,  # Aktuelles Gitter (Psi(t))
        prev_fmunu,  # Gitter des vorherigen Zeitschritts (Psi(t-dt))
        d,  # Räumlicher Gitterabstand d
        dt,  # Zeitschrittweite
        p_axes, m_axes,  # ([+dirs], [-dirs])
):

    # 1. Funktion für die räumliche Zentraldifferenz
    @jit
    def _d_spatial(field_forward, field_backward, d_space):
        """Berechnet (Psi_{i+1} - Psi_{i-1}) / (2.0 * d) für das gesamte Array."""
        return (field_forward - field_backward) / (2.0 * d_space)

    # 2. Funktion für die zeitliche Ableitung (Backward Difference)
    def _d_time(field_current, field_prev, d_time):
        """Berechnet (Psi(t) - Psi(t-dt)) / dt für das gesamte Array."""
        return (field_current - field_prev) / d_time

    # --- Räumliche Ableitungen (Batch-Verarbeitung der 13 Paare) ---

    def _calc_spatial_derivative(dir_p, dir_m):
        # np und nm sind die VOLLSTÄNDIGEN verschobenen Gitter-Arrays
        np = jnp.roll(fmunu, shift=dir_p, axis=(0, 1, 2, 3))
        nm = jnp.roll(fmunu, shift=dir_m, axis=(0, 1, 2, 3))

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
        field_current=fmunu,
        field_prev=prev_fmunu,
        d_time=dt
    )

    # Konvertierung des Array-Ergebnisses des vmap-Kerns in eine Liste von Arrays
    dmu_fmunu = list(dmu_spatial)

    # Zeitlichen Term an erster Stelle einfügen
    dmu_fmunu.insert(0, time_res)

    return dmu_fmunu


