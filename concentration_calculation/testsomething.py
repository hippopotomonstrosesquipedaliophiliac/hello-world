import numpy as np
import sympy as sp
from scipy.stats import linregress
def estimate_convergent_sum(data, p_estimate):
    partial_sum = sum(data)
    N = len(data)
    if p_estimate > 1:
        tail_estimate = (N**(1 - p_estimate)) / (p_estimate - 1)
    else:
        tail_estimate = np.inf  # Divergent
    print(tail_estimate)
    total_estimate = partial_sum + tail_estimate
    return total_estimate, partial_sum, tail_estimate

def check_convergence_full(data):
    data = np.array(data, dtype=float)
    n = np.arange(1, len(data) + 1)

    # Step 1: Monotonic decreasing and tending to zero
    is_decreasing = np.all(np.diff(data) <= 0)
    tends_to_zero = data[-1] == 0 or np.isclose(data[-1], 0, atol=1e-8)
    # Step 2: Ratio test
    ratios = data[1:] / data[:-1]
    avg_ratio = np.mean(ratios)
    ratio_test_convergent = avg_ratio < 1

    # Step 3: Log-Log Regression for p-series detection
    positive_mask = data > 0
    log_n = np.log(n[positive_mask])
    log_data = np.log(data[positive_mask])
    slope, intercept, r_value, p_value, std_err = linregress(log_n, log_data)
    p_estimate = -slope
    p_series_convergent = p_estimate > 1

    # Final verdict
    if not is_decreasing or not tends_to_zero:
        verdict = "Divergent: sequence not decreasing or tending to zero"
    elif ratio_test_convergent:
        verdict = "Likely convergent: Ratio test satisfied"
    elif p_series_convergent:
        verdict = f"Likely convergent: behaves like 1/n^{p_estimate:.2f} with p > 1"
    else:
        verdict = "Divergent or inconclusive"

    # Output
    return {
        "is_decreasing": is_decreasing,
        "tends_to_zero": tends_to_zero,
        "average_ratio": avg_ratio,
        "p_estimate": p_estimate,
        "verdict": verdict
    }
data = [1.0, 0.25, 0.1111, 0.0625, 0.04, 0.0277, 0.0204, 0.0156, 0.0123,1e-8]
result = check_convergence_full(data)
convergence_estimate=[ estimate_convergent_sum(data, result['p_estimate'])]
for k, v in result.items():
    print(f"{k}: {v}")
for est in convergence_estimate:
    print(est)