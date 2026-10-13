"""Closed-form micromagnetic estimates, for sanity-checking a simulation.

None of these replace the simulation. They exist so that a result can be
compared against something independent: if a simulated wall is four times
wider than pi*sqrt(A/Keff), one of the two is wrong, and it is worth finding
out which before the number reaches a figure.

Every function states its assumptions. Where a convention is contested the
docstring says so, because the disagreement is usually a factor of pi or a
factor of two and that is exactly the size of error that goes unnoticed.

SI throughout, matching mumax3: A in J/m, Ms in A/m, K in J/m^3, B in T.
"""

from __future__ import annotations

import math

MU0 = 4e-7 * math.pi          # T*m/A
GAMMA_LL = 1.7595e11          # rad/(T*s), mumax3's default GammaLL
GAMMA_2PI = GAMMA_LL / (2 * math.pi)   # ~2.80e10 Hz/T = 28 GHz/T


def exchange_length(A: float, Ms: float) -> float:
    """Magnetostatic exchange length, l_ex = sqrt(2A / (mu0 Ms^2)).

    The length below which exchange dominates dipolar energy. The standard
    rule of thumb is that the cell must not exceed it, or a domain wall cannot
    be resolved.

    Permalloy (A=13e-12, Ms=800e3) -> 5.7 nm.
    """
    if Ms <= 0:
        raise ValueError("Ms must be positive")
    return math.sqrt(2 * A / (MU0 * Ms * Ms))


def k_eff(Ku1: float, Ms: float) -> float:
    """Effective perpendicular anisotropy with thin-film shape anisotropy
    removed: Keff = Ku1 - mu0 Ms^2 / 2.

    Assumes an extended film magnetised out of plane (demag factor Nz = 1).
    Negative Keff means shape wins and the film lies in plane.
    """
    return Ku1 - MU0 * Ms * Ms / 2


def wall_parameter(A: float, K: float) -> float:
    """Wall width parameter Delta = sqrt(A/K).

    This is the length in the tanh(x/Delta) profile. It is NOT the quantity
    most papers call "the domain wall width" -- see wall_width.
    """
    if K <= 0:
        raise ValueError("K must be positive (in-plane easy axis has no PMA wall)")
    return math.sqrt(A / K)


def wall_width(A: float, K: float) -> float:
    """Domain wall width delta = pi * sqrt(A/K).

    The Lilley/Bloch definition, and the one usually quoted. Note the factor
    of pi: sqrt(A/K) alone is the wall *parameter* Delta, a factor 3.14
    smaller. Reporting one where the other is meant is a common error.
    """
    return math.pi * wall_parameter(A, K)


def critical_dmi(A: float, K: float) -> float:
    """DMI above which the uniform state gives way to a spiral,
    D_c = 4 sqrt(A*Keff) / pi.

    Use Keff (shape anisotropy already subtracted). Above D_c a uniform film
    is unstable; isolated skyrmions are typically found somewhat below it.
    """
    if K <= 0:
        raise ValueError("Keff must be positive for this estimate")
    return 4 * math.sqrt(A * K) / math.pi


def fmr_in_plane(B: float, Ms: float, gamma_2pi: float = GAMMA_2PI) -> float:
    """Kittel resonance of a thin film magnetised in plane, field in plane:

        f = (gamma/2pi) * sqrt( B * (B + mu0 Ms) )

    Assumes an extended film (Nx = Ny = 0, Nz = 1), no anisotropy, B along the
    magnetisation. Returns Hz.
    """
    inner = B * (B + MU0 * Ms)
    if inner < 0:
        return 0.0
    return gamma_2pi * math.sqrt(inner)


def fmr_out_of_plane(B: float, Ms: float, Ku1: float = 0.0,
                     gamma_2pi: float = GAMMA_2PI) -> float:
    """Kittel resonance of a thin film magnetised out of plane:

        f = (gamma/2pi) * ( B - mu0 Ms + 2 Ku1 / Ms )

    Valid only once the field has saturated the film out of plane; below that
    the film is not uniformly magnetised and the formula does not apply.
    Returns Hz, clamped at zero.
    """
    aniso = (2 * Ku1 / Ms) if Ms > 0 else 0.0
    f = gamma_2pi * (B - MU0 * Ms + aniso)
    return max(f, 0.0)


def walker_field(alpha: float, K_perp: float, Ms: float) -> float:
    """Walker breakdown field in the 1D model, B_W = alpha * K_perp / Ms (T).

    K_perp is the anisotropy that the wall MOMENT feels when it turns between
    the Bloch and the Neel structure -- NOT the uniaxial K (or Keff) that sets
    the wall width. Passing Keff here overestimates B_W by 1-2 orders of
    magnitude in thin films. For a thin film without DMI, K_perp is the wall's
    own demagnetising anisotropy (see wall_demag_anisotropy); with interfacial
    DMI use walker_field_dmi.

    1D rigid-wall model: real strips deviate by tens of percent (wall tilt,
    finite width, edges), so read the result as "breakdown is around here".
    """
    if Ms <= 0:
        raise ValueError("Ms must be positive")
    return alpha * K_perp / Ms


def wall_demag_anisotropy(t: float, Delta: float, Ms: float) -> float:
    """Bloch-Neel anisotropy of a wall in an ultrathin film, K_D = N_x mu0 Ms^2 / 2
    with N_x ~ t ln2 / (pi Delta) (Tarasenko et al. 1998), in J/m^3. Thin film
    (t << Delta); the Bloch wall is the lower-energy structure without DMI."""
    return t * math.log(2) / (math.pi * Delta) * MU0 * Ms * Ms / 2


def walker_field_thiaville(alpha: float, D: float, Ms: float, Delta: float, t: float) -> float:
    """Walker field of a thin-film wall with interfacial DMI AND its own demagnetising anisotropy, from the 1D
    q-phi model (Thiaville et al., EPL 100, 57002, 2012): B_W = alpha sin(phi_W) [(pi/2) B_DMI - B_K cos(phi_W)],
    cos(phi_W) = (delta - sqrt(delta^2 + 8))/4, delta = (pi/2) B_DMI / B_K, with B_DMI = D/(Ms Delta) and
    B_K = 2 K_D / Ms. Reduces to alpha B_K / 2 at D = 0 and to (pi/2) alpha B_DMI at large D. In T."""
    B_K = 2 * wall_demag_anisotropy(t, Delta, Ms) / Ms
    B_D = abs(D) / (Ms * Delta)
    delta = (math.pi / 2) * B_D / B_K
    c = (delta - math.sqrt(delta * delta + 8)) / 4
    return alpha * math.sqrt(1 - c * c) * ((math.pi / 2) * B_D - B_K * c)


def walker_field_dmi(alpha: float, D: float, Ms: float, Delta: float) -> float:
    """Walker field of a Neel wall stabilised by interfacial DMI, when the DMI
    dominates the wall's own demagnetising anisotropy (Thiaville et al., EPL 100,
    57002, 2012): B_W ~ (pi/2) alpha D / (Ms Delta), in T. 1D model; real strips
    deviate by tens of percent."""
    if Ms <= 0 or Delta <= 0:
        raise ValueError("Ms and Delta must be positive")
    return math.pi / 2 * alpha * abs(D) / (Ms * Delta)


def wall_mobility(alpha: float, gamma_ll: float = GAMMA_LL) -> float:
    """Steady-state wall mobility below Walker breakdown, in (m/s)/T per unit
    wall width: v = (gamma/alpha) * Delta * B.

    Returns gamma/alpha; multiply by Delta (wall parameter) and B to get a
    velocity. Only valid below the Walker field.
    """
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    return gamma_ll / alpha


def demag_factors_thin_film() -> tuple[float, float, float]:
    """(Nx, Ny, Nz) for an extended thin film: (0, 0, 1)."""
    return (0.0, 0.0, 1.0)


def demag_factor_sphere() -> tuple[float, float, float]:
    """(Nx, Ny, Nz) for a sphere: (1/3, 1/3, 1/3)."""
    return (1 / 3, 1 / 3, 1 / 3)


def cells_per_wall(cell: float, A: float, K: float) -> float:
    """How many cells span a domain wall. Below ~4 the wall is a staircase and
    velocities and coercive fields are unreliable."""
    return wall_width(A, K) / cell


def summarise(Ms: float, A: float, Ku1: float = 0.0, alpha: float | None = None,
              cell: float | None = None, D: float | None = None, t: float | None = None) -> dict:
    """Every estimate that the given parameters support.

    Returns a dict of name -> (value, unit, note). Entries whose assumptions
    are not met are omitted rather than reported as zero.
    """
    out: dict[str, tuple] = {}
    lex = exchange_length(A, Ms)
    out["exchange_length"] = (lex, "m", "cell should not exceed this")

    Keff = k_eff(Ku1, Ms) if Ku1 else None
    if Ku1:
        out["k_eff"] = (Keff, "J/m3",
                        "Ku1 - mu0 Ms^2/2; negative means in-plane easy axis")

    if Keff and Keff > 0:
        out["wall_parameter"] = (wall_parameter(A, Keff), "m", "Delta in tanh(x/Delta)")
        out["wall_width"] = (wall_width(A, Keff), "m", "pi*Delta, the usual quoted width")
        out["critical_dmi"] = (critical_dmi(A, Keff), "J/m2",
                               "above this the uniform state spirals")
        Delta = wall_parameter(A, Keff)
        if alpha and D and t:
            out["walker_field"] = (walker_field_thiaville(alpha, D, Ms, Delta, t), "T",
                                   "1D model with DMI and the wall's own anisotropy (Thiaville 2012)")
        elif alpha and D:
            out["walker_field"] = (walker_field_dmi(alpha, D, Ms, Delta), "T",
                                   "1D, large-D limit (pi/2) alpha D/(Ms Delta); low if D is near the Neel "
                                   "threshold: give --t")
        elif alpha and t:
            out["walker_field"] = (walker_field(alpha, wall_demag_anisotropy(t, Delta, Ms), Ms), "T",
                                   "1D model, thin film without DMI: alpha K_D/Ms")
        if t:
            out["neel_threshold_dmi"] = (2 * math.log(2) * MU0 * Ms * Ms * t / math.pi ** 2, "J/m2",
                                         "above this D the wall is fully Neel (thin film)")
        if cell:
            out["cells_per_wall"] = (cells_per_wall(cell, A, Keff), "",
                                     "below ~4 the wall is under-resolved")
        if D is not None:
            dc = critical_dmi(A, Keff)
            out["dmi_ratio"] = (D / dc if dc else float("inf"), "",
                                "D/D_c; >1 means no uniform state")

    if cell:
        out["cells_per_exchange_length"] = (lex / cell, "",
                                            "should be >= 1")

    out["fmr_in_plane_at_0.1T"] = (fmr_in_plane(0.1, Ms) / 1e9, "GHz",
                                   "Kittel, extended film, no anisotropy")
    return out
