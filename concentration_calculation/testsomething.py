import sympy as sp

# Variable
x = sp.symbols('x')

# --- Parameters (edit these) ---
n, m, k = 2, 4, 100                 # exponents
logC_value = sp.log(5)                    # this is your assigned constant value for log(C)
# --------------------------------

# Log arguments
A = 3 - 2*x
B = 4 - 5*x
D = 3 + 100*x

# Domain (natural log): arguments must be > 0
domain = sp.And(A > 0, B > 0, D > 0)   # => -3 < x < 0.8

# Build equation: log(C) = n*log(A) + m*log(B) - k*log(D)
# With log(C) assigned to a constant logC_value:
f = n*sp.log(A) + m*sp.log(B) - k*sp.log(D) - logC_value
print(f)
# We’ll find real roots inside the domain using nsolve with multiple seeds
xmin, xmax = -3.0 + 1e-9, 0.8 - 1e-9

roots = []
# Sample seeds across the interval; nsolve is local, so use many starting points
for seed in [xmin + (xmax - xmin)*t/100 for t in range(101)]:
    try:
        r = sp.nsolve(f, seed)
        r = float(sp.N(r))
        # keep only roots inside domain and de-duplicate (within tolerance)
        if xmin < r < xmax and all(abs(r - s) > 1e-7 for s in roots):
            roots.append(r)
    except (sp.SympifyError, ValueError, TypeError):
        pass

roots.sort()
print("Real solutions in domain (-3, 0.8):", roots)
