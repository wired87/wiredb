import jax.numpy as jnp
from jax import jit, vmap


@jit
def calc_yterm(y, psi, psi_bar, h):
    """
    Time evolution (for sim)
    Uses Kinetic derivation & coupling term of neighbors
    """

    def _yukawa_term(
        y, psi, psi_bar, neighbor_h
    ):
        yterm = -y * neighbor_h * jnp.vdot(psi_bar, psi)
        return yterm

    yterm = vmap(
        _yukawa_term, in_axes=(
        0,0,0,0
    ))(
        y,
        psi,
        psi_bar,
        h
    )

    return yterm


# --------------------
# psi_bar s(konjugierter Spinor)
# --------------------
@jit
def calc_psi_bar(psi, gamma):
    psi_bar = psi.conj().T @ gamma[0]
    return psi_bar

# --------------------
# dmu_psi
# --------------------
@jit
def calc_dmu_psi(
        psi,  # entire gitter
        prev_psi,  # Gitter des vorherigen Zeitschritts (Psi(t-dt))
        d,  # Räumlicher Gitterabstand d
        dt,
        p_axes, m_axes,
):
    # 1. Funktion für die räumliche Zentraldifferenz
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
        np = jnp.roll(psi, shift=dir_p, axis=(0, 1, 2, 3))
        nm = jnp.roll(psi, shift=dir_m, axis=(0, 1, 2, 3))

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
        field_current=psi,
        field_prev=prev_psi,
        d_time=dt
    )

    # Konvertierung des Array-Ergebnisses des vmap-Kerns in eine Liste von Arrays
    dmu_psi = list(dmu_spatial)

    # Zeitlichen Term an erster Stelle einfügen
    dmu_psi.insert(0, time_res)

    return dmu_psi


# --------------------
# dirac_process
# --------------------
@jit
def calc_dirac(psi, dmu_psi, _mass, gterm, yterm, gamma, gamma0_inv, i):
    """
    Time evolution (for sim)
    Uses Kinetic derivation & coupling term of neighbor gauges
    """
    spatial = jnp.zeros_like(psi, dtype=complex)

    def _wrapper(mu):
        # γ^i @ μ with chosen gamma index i (keeps original intent)
        gamma_item = gamma[i]
        dmu_x = gamma_item @ mu
        return dmu_x

    vmapped_func = vmap(_wrapper, in_axes=(0))
    compiled_kernel = jit(vmapped_func)

    spatial = spatial + jnp.sum(compiled_kernel(dmu_psi), axis=0)
    spatial = spatial + gterm + yterm

    mass_term = -1j * _mass * psi
    dirac = -gamma0_inv @ (spatial + mass_term)

    #jax.debug.print(" dirac_process result: {dirac}", dirac=dirac_result)
    return dirac


# --------------------
# psi update
# --------------------
@jit
def calc_psi(psi, dt, dirac):
    psi = psi + dt * dirac
    #jax.debug.print("🔁 psi_update: {updated}", updated=updated)
    return psi


@jit
def calc_gterm(psi, i, field_value, g, T):
    """
    Vectorized neighbor coupling calculation.
    g_neighbors: array-like with entries (g, field_value, T)
    - field_value expected shape: (4, ...) or (mu,...)
    - T: color matrix acting on psi
    """

    def _calculate_single_neighbor_coupling(
            field_value, g, T
    ):
        # single_mu_term returns gterm for one mu component
        def _single_mu_term(field_value):
            # -i * g * A_mu * (T @ psi)
            gterm = -i * g * field_value * (T @ psi)
            return gterm

        # vmap over mu axis (first axis of field_value)
        four_terms = vmap(_single_mu_term, in_axes=(0))(field_value)
        return jnp.sum(four_terms, axis=0)

    # vmap across neighbors
    vmapped = vmap(
        _calculate_single_neighbor_coupling,
        in_axes=(0, None, 0)
    )
    compiled_kernel = jit(vmapped)(
        field_value, g, T
    )

    gterm = jnp.sum(compiled_kernel, axis=0)
    ##jax.debug.print("🔗 ferm_g_coupling_process result norm: {n}", n=jnp.linalg.norm(gterm))
    return gterm


# --------------------
# _add_coupling_term
# --------------------
def _add_coupling_term(nid, nnid, gauge_total_coupling, all_subs):
    """
    Update edge coupling term in provided all_subs structure.
    all_subs expected to be a dict with key "EDGES" mapping edge_key -> attrs dict.
    """
    if gauge_total_coupling is None:
        print(" add_coupling_term: gauge_total_coupling is None, nothing done.")
        return

    for k, v in all_subs.get("EDGES", {}).items():
        if nid in k and nnid in k:
            v.update({"coupling_term": gauge_total_coupling})
            print("add_coupling_term updated:", k, v)


# --------------------
# gauss          - - -
# --------------------
@jit
def _gauss(x, mu=0, sigma=5):
    res = jnp.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
    #jax.debug.print(" gauss: x={x}, res_norm={norm}", x=x, norm=jnp.linalg.norm(res))
    return res


# --------------------
# get_quark_doublet
# --------------------
def _get_quark_doublet(short_lower_type, psi, id, ckm, all_subs):

    partner_map = {
        "up": "down",
        "charm": "strange",
        "top": "bottom",
    }

    if short_lower_type not in partner_map:
        raise ValueError(f"Kein gültiger Quarktyp für W-Kopplung: {short_lower_type}")

    total_down_psi_sum = jnp.zeros_like(psi, dtype=complex)

    ckm_struct = ckm  # already passed in

    for quark_type, ckm_val in ckm_struct.items():
        quark_key = f"{quark_type}_quark".upper()
        neighbor_quark = all_subs["FERMION"].get(quark_key, {})
        if not neighbor_quark:
            # no neighbor found -> skip
            continue

        # extract first neighbor entry (mimic original)
        item_paare = list(neighbor_quark.items())[0]
        item_attrs = item_paare[1]
        neighbor_psi = item_attrs.get("psi")

        n_handedness = item_attrs.get("handedness", None)
        if n_handedness and isinstance(n_handedness, str) and n_handedness == "left":
            component = neighbor_psi * ckm_val
        else:
            component = 0

        total_down_psi_sum += component

    doublet = jnp.stack([psi, total_down_psi_sum], axis=1)
    print(f"get_quark_doublet produced shape {doublet.shape}")
    return doublet


