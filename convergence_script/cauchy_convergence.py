
def check_cauchy(sequence: list[float | int],
                 epsilon: float,
                 subseq_len: int | None) -> bool:

    """
    The Cauchy check for convergence states that for a sequence (x_1, x_2, x_3, ...)
    For all eps > 0, there exists some constant N such that for all m, n > N,
    |x_m - x_n| < eps
    """
    #If no length give, check the entire sequence
    if subseq_len is None:
        subsequence = sequence
    else:
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
                   subseq_len: int | None) -> bool:
    """
    The typical check for convergence states that for a sequence (x_1, x_2, x_3, ...)
    for any epsilon > 0
    there exists a number N such that |x_n - limit| < epsilon, for numbers n > N
    """
    #If no subsequence length given, then we check the entire sequence
    if subseq_len is None:
        subsequence = sequence
    else:
        subsequence = sequence[-subseq_len:]

    limit = sequence[-1]
    for n in range(len(subsequence)):
        if abs(subsequence[n] - limit) > epsilon:
            print(f"Sequence fails convergence test at |{subsequence[n]} - {limit}| = |{subsequence[n] - limit}| > {epsilon}")
            return False
        
    print(f"Sequence converges to {limit}")
    return True

def oscillatory_check(sequence: list[int | float],
                      epsilon: float):
    """
    Super Experimental Code for detecting oscillatory behavior.
    Currently returns a list of lists, where the second value is the # of times that value gets close to a previous value.
    For example, with the list [1, 2, 3.9, 4, 5], epsilon = 1,
    The returned values would be
    [[1, 0], [2, 0], [3.9, 0], [4, 1], [5, 0]] since 4 gets close to 1 previous value (3.9)
    You can mess around with this
    """
    values_to_check: list[list[float|int]] = [[i, 0] for i in sequence]
    for i in range(len(values_to_check)):
        for j in range(i+1, len(values_to_check)):
            if abs(values_to_check[i][0] - values_to_check[j][0]) < epsilon:
                values_to_check[j][1] += 1
    print(values_to_check)


oscillatory_check([1, 2, 3.9, 4, 5], epsilon=1)
        

    
    

