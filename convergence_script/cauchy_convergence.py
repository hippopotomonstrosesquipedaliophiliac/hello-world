
def check_cauchy(sequence: list[float | int],
                 epsilon: float,
                 subseq_len: int) -> bool:

    """
    The Cauchy check for convergence states that for a sequence (x_1, x_2, x_3, ...)
    For all eps > 0, there exists some constant N such that for all m, n > N,
    |x_m - x_n| < eps
    """

    subsequence = sequence[-subseq_len:]
    for m in range(len(subsequence)):
        for n in range(m+1, len(subsequence)):
            if abs(subsequence[m] - subsequence[n]) > epsilon:
                print(f"Sequence fails Cauchy test at |{subsequence[m] - subsequence[n]}| = |{subsequence[m] - subsequence[n]}| > {epsilon}")
                return False
            
    print(f"Sequence is a Cauchy sequence that converges to {sequence[-1]}")
    return True


def check_converge(sequence: list[float | int],
                   epsilon: float,
                   subseq_len: int) -> bool:
    """
    The typical check for convergence states that for a sequence (x_1, x_2, x_3, ...)
    for any epsilon > 0
    there exists a number N such that |x_n - limit| < epsilon, for numbers n > N
    """
    subsequence = sequence[-subseq_len:]
    limit = sequence[-1]
    for n in range(len(subsequence)):
        if abs(subsequence[n] - limit) > epsilon:
            print(f"Sequence fails convergence test at |{subsequence[n]} - {limit}| = |{subsequence[n] - limit}| > {epsilon}")
            return False
        
    print(f"Sequence converges to {limit}")
    return True
    
    

