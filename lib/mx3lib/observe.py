"""Turning a table into the quantity a researcher actually asked about.

"Did the skyrmion survive", "what is the coercive field", "how fast is the
wall", "has it settled" -- these are the things people want, and none of them
is a column in table.txt. Each function here answers one, and each returns
enough context to say *why* rather than just a number.

Standard library only, so this runs wherever mumax3 does. The tables are a few
thousand rows; a Python loop is not the bottleneck.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# hysteresis
# ---------------------------------------------------------------------------

@dataclass
class LoopMetrics:
    coercivity: float | None      # T, field where m crosses zero
    remanence: float | None       # m at B = 0
    saturation: float | None      # max |m|
    branches: int                 # how many monotonic field sweeps were found
    squareness: float | None      # remanence / saturation
    note: str = ""


def _zero_crossings(x: list[float], y: list[float]) -> list[float]:
    """x where y changes sign, linearly interpolated."""
    out = []
    for i in range(len(y) - 1):
        y0, y1 = y[i], y[i + 1]
        if y0 == 0:
            out.append(x[i])
        elif (y0 < 0) != (y1 < 0):
            t = y0 / (y0 - y1)
            out.append(x[i] + t * (x[i + 1] - x[i]))
    return out


def _split_branches(B: list[float]) -> list[tuple[int, int]]:
    """Index ranges over which the field sweeps monotonically."""
    if len(B) < 3:
        return [(0, len(B))]
    spans, start = [], 0
    sign = 0
    for i in range(1, len(B)):
        d = B[i] - B[i - 1]
        if d == 0:
            continue
        s = 1 if d > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            spans.append((start, i))
            start, sign = i - 1, s
    spans.append((start, len(B)))
    return [s for s in spans if s[1] - s[0] >= 2]


def hysteresis(B: list[float], m: list[float]) -> LoopMetrics:
    """Coercivity, remanence and squareness from a swept loop.

    `B` is the field component along the sweep axis, `m` the magnetisation
    component along it. Both come straight from table.txt columns.

    Coercivity is reported as the mean |B| over all zero crossings, so a
    symmetric loop gives one number. An asymmetric loop is flagged in `note`
    rather than averaged away silently.
    """
    if len(B) != len(m) or len(B) < 3:
        return LoopMetrics(None, None, None, 0, None, "too few points")

    crossings = _zero_crossings(B, m)
    branches = _split_branches(B)

    coercivity = None
    note = ""
    if crossings:
        mags = [abs(c) for c in crossings]
        coercivity = sum(mags) / len(mags)
        spread = (max(mags) - min(mags)) if len(mags) > 1 else 0.0
        if coercivity > 0 and spread / coercivity > 0.1:
            note = (f"asymmetric loop: crossings at "
                    f"{', '.join(f'{c:.4g}' for c in crossings)} T")
    else:
        note = "m never crosses zero - field range may not reach switching"

    # remanence: |m| at the field nearest zero
    i0 = min(range(len(B)), key=lambda i: abs(B[i]))
    remanence = abs(m[i0])
    if abs(B[i0]) > 1e-6:
        note = (note + "; " if note else "") + \
               f"no point at B=0 (nearest {B[i0]:.3g} T), remanence approximate"

    saturation = max(abs(v) for v in m)
    squareness = remanence / saturation if saturation else None

    return LoopMetrics(coercivity, remanence, saturation, len(branches),
                       squareness, note)


# ---------------------------------------------------------------------------
# motion
# ---------------------------------------------------------------------------

@dataclass
class VelocityFit:
    velocity: float           # m/s
    r_squared: float          # 1.0 = perfectly linear
    window: tuple[int, int]   # rows used
    note: str = ""


def velocity(t: list[float], pos: list[float], skip_fraction: float = 0.3) -> VelocityFit:
    """Steady-state velocity from a position trace, by least squares.

    The first `skip_fraction` of the trace is dropped: a wall or skyrmion
    accelerates before it reaches terminal velocity, and including the
    transient biases the fit low.

    r_squared is reported because a poor fit is meaningful -- oscillating
    position after Walker breakdown gives a low r^2, and a velocity quoted from
    that is not a steady-state velocity at all.
    """
    n = len(t)
    if n != len(pos) or n < 4:
        return VelocityFit(float("nan"), 0.0, (0, n), "too few points")

    start = int(n * skip_fraction)
    ts, ps = t[start:], pos[start:]
    k = len(ts)
    mt, mp = sum(ts) / k, sum(ps) / k
    sxx = sum((v - mt) ** 2 for v in ts)
    if sxx == 0:
        return VelocityFit(float("nan"), 0.0, (start, n), "time does not advance")
    sxy = sum((ts[i] - mt) * (ps[i] - mp) for i in range(k))
    slope = sxy / sxx

    syy = sum((v - mp) ** 2 for v in ps)
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 1.0

    note = ""
    if r2 < 0.9:
        note = (f"poor linear fit (r^2={r2:.2f}); motion is not steady - "
                f"oscillation past Walker breakdown, pinning, or too short a run")
    return VelocityFit(slope, r2, (start, n), note)


# ---------------------------------------------------------------------------
# settling
# ---------------------------------------------------------------------------

@dataclass
class Settling:
    settled: bool
    drift: float              # relative change across the tail
    tail_fraction: float
    note: str = ""


def settled(values: list[float], tail_fraction: float = 0.2,
            tolerance: float = 1e-3) -> Settling:
    """Has the quantity stopped changing?

    Compares the mean of the final `tail_fraction` against the mean of the
    segment before it, relative to the overall range. Used to decide whether a
    run was long enough -- a trajectory still drifting at the last step has not
    reached the state being reported.
    """
    n = len(values)
    if n < 10:
        return Settling(False, float("nan"), tail_fraction, "too few points to judge")

    k = max(2, int(n * tail_fraction))
    tail = values[-k:]
    prev = values[-2 * k:-k] if n >= 2 * k else values[:-k]
    if not prev:
        return Settling(False, float("nan"), tail_fraction, "too few points to judge")

    mt, mp = sum(tail) / len(tail), sum(prev) / len(prev)
    span = max(values) - min(values)
    scale = span if span > 0 else (abs(mt) if mt else 1.0)
    drift = abs(mt - mp) / scale

    ok = drift < tolerance
    note = "" if ok else (
        f"still drifting by {drift:.2%} of its range over the last "
        f"{tail_fraction:.0%} - the run may be too short"
    )
    return Settling(ok, drift, tail_fraction, note)


# ---------------------------------------------------------------------------
# convergence across runs
# ---------------------------------------------------------------------------

@dataclass
class Convergence:
    converged: bool
    converged_at: float | None    # the coarsest setting that is good enough
    series: list[tuple[float, float]]
    tolerance: float
    note: str = ""


def convergence(points: list[tuple[float, float]], tolerance: float = 0.02
                ) -> Convergence:
    """Given (setting, observable) pairs, find the coarsest setting whose
    answer is within `tolerance` of the finest.

    `setting` is typically cell size. Pairs are sorted fine-to-coarse
    internally, and the finest run is taken as the reference -- which is an
    assumption, not a proof: if even the finest is unconverged the whole series
    is, and that is reported rather than hidden.
    """
    if len(points) < 3:
        return Convergence(False, None, points, tolerance,
                           "need at least three settings to see a trend")

    pts = sorted(points, key=lambda p: p[0])
    ref = pts[0][1]
    if ref == 0:
        return Convergence(False, None, pts, tolerance,
                           "reference value is zero; cannot judge relative change")

    ok = [(s, v) for s, v in pts if abs(v - ref) / abs(ref) <= tolerance]
    coarsest = max((s for s, _ in ok), default=None)

    # If the two finest disagree, the reference itself is suspect.
    finest_gap = abs(pts[1][1] - pts[0][1]) / abs(ref)
    if finest_gap > tolerance:
        return Convergence(
            False, None, pts, tolerance,
            f"the two finest settings still differ by {finest_gap:.1%} - the "
            f"series has not converged anywhere; refine further before trusting any of it",
        )

    return Convergence(True, coarsest, pts, tolerance,
                       f"answers agree within {tolerance:.0%} for settings "
                       f"at or below {coarsest:g}")


# ---------------------------------------------------------------------------
# spectra
# ---------------------------------------------------------------------------

def spectrum(t: list[float], y: list[float], detrend: bool = True
             ) -> tuple[list[float], list[float]]:
    """Amplitude spectrum of a uniformly sampled trace, via a plain DFT.

    Returns (frequencies_Hz, amplitudes) up to Nyquist. Intended for reading a
    resonance off an FMR ringdown, where the traces are short. O(n^2), so it
    refuses anything long enough to matter -- use numpy for those.
    """
    n = len(y)
    if n != len(t) or n < 8:
        raise ValueError("need at least 8 uniformly sampled points")
    if n > 4096:
        raise ValueError(
            f"{n} points is too many for the built-in DFT; export to numpy and "
            f"use numpy.fft instead"
        )

    dt = (t[-1] - t[0]) / (n - 1)
    if dt <= 0:
        raise ValueError("time does not advance uniformly")

    vals = list(y)
    if detrend:
        mean = sum(vals) / n
        vals = [v - mean for v in vals]

    freqs, amps = [], []
    for k in range(n // 2):
        re = im = 0.0
        for j, v in enumerate(vals):
            ang = -2 * math.pi * k * j / n
            re += v * math.cos(ang)
            im += v * math.sin(ang)
        freqs.append(k / (n * dt))
        amps.append(2 * math.sqrt(re * re + im * im) / n)
    return freqs, amps


def peak_frequency(t: list[float], y: list[float]) -> tuple[float, float]:
    """Dominant frequency (Hz) and its amplitude, ignoring DC."""
    f, a = spectrum(t, y)
    if len(a) < 2:
        return (0.0, 0.0)
    i = max(range(1, len(a)), key=lambda j: a[j])
    return (f[i], a[i])
