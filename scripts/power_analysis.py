"""Power analysis for the judge-audit study (run BEFORE any data collection).

Question: with N gold items, how large must the difference in
human-agreement rate between two judges be, to be detectable?

Design: both judges are scored against the same gold labels on the same
items -> paired binary outcomes (agree/disagree with gold). We test the
difference with McNemar's exact-style test on discordant pairs, and
estimate power by simulation.

Judges' errors are correlated (they fail on the same hard items), which
*increases* power for a paired test; we simulate a grid of error
correlations to bracket reality.

Usage: python scripts/power_analysis.py
Deterministic (fixed seed). Pure stdlib.
"""

import math
import random

ALPHA = 0.05
POWER_TARGET = 0.80
N_SIM = 3000
SEED = 20260813


def simulate_pair(n, p1, p2, rho, rng):
    """Draw paired agreement outcomes for two judges on n items.

    Uses a Gaussian copula to induce correlation rho between the two
    judges' agreement indicators.
    """
    z1_thresh = _norm_ppf(p1)
    z2_thresh = _norm_ppf(p2)
    b = 0  # judge1 agrees, judge2 doesn't
    c = 0  # judge2 agrees, judge1 doesn't
    for _ in range(n):
        u = rng.gauss(0, 1)
        e1 = rho ** 0.5 * u + (1 - rho) ** 0.5 * rng.gauss(0, 1)
        e2 = rho ** 0.5 * u + (1 - rho) ** 0.5 * rng.gauss(0, 1)
        a1 = e1 < z1_thresh
        a2 = e2 < z2_thresh
        if a1 and not a2:
            b += 1
        elif a2 and not a1:
            c += 1
    return b, c


def _norm_ppf(p):
    """Acklam's rational approximation of the standard normal quantile."""
    if not 0 < p < 1:
        raise ValueError(p)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def mcnemar_p(b, c):
    """Two-sided exact binomial McNemar test on discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # two-sided exact binomial, p=0.5
    total = 0.0
    for i in range(0, k + 1):
        total += math.comb(n, i) * 0.5 ** n
    p = 2 * total
    # correction when b == c (avoid double counting the center term)
    if b == c:
        p -= math.comb(n, k) * 0.5 ** n
    return min(1.0, p)


def power(n, p_base, delta, rho, rng):
    hits = 0
    for _ in range(N_SIM):
        b, c = simulate_pair(n, p_base + delta, p_base, rho, rng)
        if mcnemar_p(b, c) < ALPHA:
            hits += 1
    return hits / N_SIM


def main():
    rng = random.Random(SEED)
    print(f"alpha={ALPHA}, target power={POWER_TARGET}, sims={N_SIM}")
    print()
    for n in (300, 450, 600):
        for p_base in (0.70, 0.80):
            for rho in (0.2, 0.5):
                # find minimal detectable delta by scanning
                mdd = None
                for delta_pp in range(2, 16):
                    delta = delta_pp / 100
                    if p_base + delta >= 0.99:
                        break
                    pw = power(n, p_base, delta, rho, rng)
                    if pw >= POWER_TARGET:
                        mdd = (delta_pp, pw)
                        break
                if mdd:
                    print(f"N={n:4d} base_agree={p_base:.2f} err_corr={rho:.1f}"
                          f"  -> minimal detectable diff = {mdd[0]} pp"
                          f" (power {mdd[1]:.2f})")
                else:
                    print(f"N={n:4d} base_agree={p_base:.2f} err_corr={rho:.1f}"
                          f"  -> >15 pp (underpowered)")
        print()


if __name__ == "__main__":
    main()
