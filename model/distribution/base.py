import numpy as np


def possion_arrival_times(lam, length, interge=True, accum=True):
    """
    Generate Poisson arrival times.

    Parameters:
    - lam: Rate parameter (lambda).
    - length: Number of arrival times to generate.

    Returns:
    - Array of Poisson arrival times.
    """
    if interge:
        intervals = np.random.poisson(lam, length) + 1
    else:
        intervals = np.random.exponential(1 / lam, length)
    if accum:
        arrival_times = np.cumsum(intervals)
    else:
        arrival_times = intervals
    return arrival_times
