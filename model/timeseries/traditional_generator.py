import numpy as np


def discrete_mean_reverting_fundamental(
    r_bar: float, kappa: float, sigma_s: float, length: int
):
    y = np.zeros(length)
    y[0] = r_bar

    for t in range(1, length):
        y[t] = max(
            0, kappa * r_bar + (1 - kappa) * y[t - 1] + np.random.normal(0, sigma_s**2)
        )

    return y


def continue_mean_reverting_fundamental(
    r_bar: float, kappa: float, sigma_s: float, length: int
):
    x = np.zeros(length)
    x[0] = r_bar

    for t in range(1, length):
        x[t] = max(
            0, kappa * r_bar + (1 - kappa) * x[t - 1] + np.random.normal(0, sigma_s)
        )

    return x


def ornstein_uhlenbeck_process_fundamental(
    r_bar: float,
    kappa: float,
    sigma_s: float,
    time_delta: float,
    prior_value: float,
):
    """
    Generate a single Ornstein-Uhlenbeck process value.

    Parameters:
    - r_bar: Long-term mean.
    - kappa: Speed of reversion.
    - sigma_s: Volatility.
    - time_delta: Time increment.
    - prior_value: Previous value of the process.

    Returns:
    - New value of the process.
    """
    miu = r_bar + (prior_value - r_bar) * np.exp(-kappa * time_delta)
    sigma = np.sqrt(sigma_s**2 * (1 - np.exp(-2 * kappa * time_delta) / (2 * kappa)))
    print(sigma)
    return np.random.normal(miu, sigma)


def ornstein_uhlenbeck_process(
    r_bar: float, kappa: float, sigma_s: float, lam: float, length: int
):
    time_intervals = np.random.exponential(1 / lam, length)
    sigma = sigma_s * np.sqrt((1 - np.exp(-2 * kappa * time_intervals) / (2 * kappa)))

    res = np.zeros(length)

    for i in range(length):
        if i == 0:
            res[i] = r_bar
        else:
            miu = r_bar + (res[i - 1] - r_bar) * np.exp(-kappa * time_intervals[i])
            res[i] = np.random.normal(miu, sigma[i])
    arrival_times = np.cumsum(time_intervals)
    return arrival_times, res
