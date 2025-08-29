import math
from typing import List, Tuple

class EquilibriumSolveError(Exception):
    pass

Species = Tuple[float, float, str]  # (stoich ν > 0, initial conc S0 > 0, name)

def log_equation_string(reactants: List[Species], products: List[Species], Keq: float,
                        convention: str = "products_over_reactants") -> str:
    """
    Build:  sum_prod ν log(S0 + ν x) - sum_react ν log(S0 - ν x) - log(Keq) = 0
    If convention == "reactants_over_products", it instead prints with -log(1/Keq).
    """
    if convention not in ("products_over_reactants", "reactants_over_products"):
        raise ValueError("convention must be 'products_over_reactants' or 'reactants_over_products'")
    lhs_terms = []
    for ν, S0, name in products:
        lhs_terms.append(f"{ν}*log({S0} + {ν}*x)")
    for ν, S0, name in reactants:
        lhs_terms.append(f"- {ν}*log({S0} - {ν}*x)")
    lhs = " + ".join(lhs_terms).replace("+ -", "- ")
    if convention == "products_over_reactants":
        rhs = f"log({Keq})"
    else:
        rhs = f"log(1/{Keq})"  # i.e., -log(Keq)
    return f"{lhs} = {rhs}"

def solve_extent_mass_action(
    reactants: List[Species],
    products:  List[Species],
    Keq: float,
    convention: str = "products_over_reactants",
    rtol: float = 1e-12,
    atol: float = 1e-14,
    max_iter: int = 100,
    echo: bool = True,
) -> float:
    """
    Solve for extent x >= 0 in the mass-action equilibrium:

        Keq = ([prod]^ν ...)/([react]^ν ...),  with
        [react]_i = S0_i - ν_i x   (must stay > 0)
        [prod]_j  = S0_j + ν_j x   (must stay > 0)

    If your C was defined as reactants/products, pass convention='reactants_over_products'.
    Returns x (float).
    """

    if Keq <= 0: raise ValueError("Keq must be > 0")
    for ν, S0, _ in reactants + products:
        if ν <= 0 or S0 < 0:
            raise ValueError("Stoichiometries must be > 0 and initial concentrations >= 0")

    # If user uses the inverse convention, flip Keq -> 1/Keq and reuse the same formula.
    if convention == "reactants_over_products":
        Keq = 1.0 / Keq

    # Domain: x in [x_lo, x_hi)
    # Reactants decrease: require S0 - ν x > 0  =>  x < S0/ν
    # Products  increase: require S0 + ν x > 0  =>  x > -S0/ν  (usually ≤ 0)
    x_hi = min((S0/ν for ν, S0, _ in reactants), default=float("inf"))
    x_lo = max([0.0] + [(-S0/ν) for ν, S0, _ in products])  # keep physical x >= 0
    if not (x_lo < x_hi):
        raise EquilibriumSolveError(f"No feasible extent: [{x_lo}, {x_hi}) is empty.")

    logKeq = math.log(Keq)

    def f(x: float) -> float:
        # sum ν log(S0 + ν x)  -  sum ν log(S0 - ν x)  - log Keq
        s = 0.0
        for ν, S0, _ in products:
            val = S0 + ν*x
            if val <= 0: return float("inf")
            s += ν * math.log(val)
        for ν, S0, _ in reactants:
            val = S0 - ν*x
            if val <= 0: return -float("inf")
            s -= ν * math.log(val)
        return s - logKeq

    def fp(x: float) -> float:
        # derivative is strictly positive (monotone increasing):
        # sum ν^2/(S0 + ν x) + sum ν^2/(S0 - ν x)
        s = 0.0
        for ν, S0, _ in products:
            s += (ν*ν) / (S0 + ν*x)
        for ν, S0, _ in reactants:
            s += (ν*ν) / (S0 - ν*x)
        return s

    # Pretty print the exact equation being solved
    if echo:
        # Fill names with actual numeric S0 labels (e.g., A_0, etc.)
        def name_or_fallback(spec, fallback_prefix):
            ν, S0, name = spec
            return (ν, S0, name if name else fallback_prefix)
        Rn = [name_or_fallback(s, f"R{i}") for i, s in enumerate(reactants, 1)]
        Pn = [name_or_fallback(s, f"P{i}") for i, s in enumerate(products, 1)]
        # Build a readable string with numeric S0 names (A_0, etc.)
        rep = []
        for ν, S0, name in Pn: rep.append(f"{ν}*log({S0} + {ν}*x)")
        for ν, S0, name in Rn: rep.append(f"- {ν}*log({S0} - {ν}*x)")
        lhs = " + ".join(rep).replace("+ -", "- ")
        print(f"Domain: x in [{x_lo:.6g}, {x_hi:.6g})")

    # Bracket root safely away from boundaries
    eps = 1e-12
    a = max(x_lo, x_lo + eps*(1+abs(x_hi)))      # nudge off lower boundary
    b = min(x_hi*(1 - eps), x_hi - eps*(1+abs(x_hi)))  # nudge off upper boundary

    fa = f(a); fb = f(b)
    if fa == 0.0: return a
    if fb == 0.0: return b

    # Because f'(x) > 0, f is monotone increasing; we need f(a) < 0 < f(b).
    if not (fa < 0 < fb):
        # Try tightening near the ends in case of extreme steepness
        for shrink in (1e-6, 1e-5, 1e-4, 1e-3):
            aa = a + shrink*(b - a)
            bb = b - shrink*(b - a)
            faa, fbb = f(aa), f(bb)
            if faa < 0 < fbb:
                a, b, fa, fb = aa, bb, faa, fbb
                break
        else:
            # If still not bracketed, there is no solution inside [x_lo, x_hi).
            raise EquilibriumSolveError(
                f"No sign change on [{x_lo}, {x_hi}). f(a)={fa:.6e}, f(b)={fb:.6e}. "
                "Check Keq convention and inputs. If your C was reactants/products, "
                "use convention='reactants_over_products'."
            )

    # Hybrid Newton (fast) + Bisection (robust)
    x = 0.5*(a + b)
    for _ in range(max_iter):
        fx = f(x)
        if abs(fx) <= atol or abs(b - a) <= rtol*(1 + abs(x)):
            return x

        dfx = fp(x)
        # Newton step
        xn = x - fx/dfx
        # only accept if it stays in the bracket
        if (a < xn < b) and math.isfinite(xn):
            x_new = xn
        else:
            x_new = 0.5*(a + b)  # fallback: bisection midpoint

        fx_new = f(x_new)
        if fx_new == 0.0:
            return x_new

        # keep the sign-change bracket (f increasing)
        if fx_new < 0:
            a, fa = x_new, fx_new
        else:
            b, fb = x_new, fx_new

        x = x_new

    raise EquilibriumSolveError("Max iterations reached without convergence.")
A0, B0, E0, D0 = 3.0, 4.0, 0.0, 1.2    # initial concentrations
m, n, k, t = 2, 4, 6, 3                 # stoichiometric coefficients
Keq = 0.12                              # standard convention: products / reactants

reactants = [(m, A0, "A"), (n, B0, "B")]
products  = [(k, E0, "E"), (t, D0, "D")]

print(log_equation_string(reactants, products, Keq))
x = solve_extent_mass_action(reactants, products, Keq,
                             convention="products_over_reactants",
                             echo=True)
print("Extent x =", x)