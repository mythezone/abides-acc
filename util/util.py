import numpy as np
import pandas as pd
from contextlib import contextmanager
import warnings
import heapq
import random
import math

try:
    from scipy.spatial.distance import pdist, squareform
except ImportError:  # Provide lightweight fallbacks if SciPy is unavailable
    def pdist(values, metric="euclidean"):
        array = np.asarray(values, dtype=float)
        if array.ndim != 2:
            array = array.reshape(-1, 1)
        n = array.shape[0]
        dists = []
        for i in range(n - 1):
            diff = array[i + 1 :] - array[i]
            if metric == "euclidean":
                dist = np.sqrt(np.sum(diff ** 2, axis=1))
            else:
                raise ValueError(f"Unsupported metric '{metric}' without SciPy.")
            dists.extend(dist.tolist())
        return np.asarray(dists, dtype=float)

    def squareform(dists):
        dists = np.asarray(dists, dtype=float)
        if dists.ndim != 1:
            raise ValueError("squareform fallback expects a 1-D condensed distance array.")
        length = dists.size
        # Solve n(n-1)/2 = length for n
        n = int((1 + math.sqrt(1 + 8 * length)) / 2)
        mat = np.zeros((n, n), dtype=float)
        idx = 0
        for i in range(n - 1):
            for j in range(i + 1, n):
                mat[i, j] = mat[j, i] = dists[idx]
                idx += 1
        return mat

from typing import List, Dict, TYPE_CHECKING, Iterable, Tuple, Optional

# if TYPE_CHECKING:
#     from order.base import Order

# General purpose utility functions for the simulator, attached to no particular class.
# Available to any agent or other module/utility.  Should not require references to
# any simulator object (kernel, agent, etc).

# Module level variable that can be changed by config files.
silent_mode = False


# This optional log_print function will call str.format(args) and print the
# result to stdout.  It will return immediately when silent mode is active.
# Use it for all permanent logging print statements to allow fastest possible
# execution when verbose flag is not set.  This is especially fast because
# the arguments will not even be formatted when in silent mode.
def log_print(msg: str, current_time: pd.Timestamp, *args):
    #   if not silent_mode:
    #         formatted = msg.format(*args)
    #     #   print (str.format(*args))
    #         logger.log(formatted,current_time)
    pass


# Accessor method for the global silent_mode variable.
def be_silent():
    return silent_mode


# Utility method to flatten nested lists.
def delist(list_of_lists):
    return [x for b in list_of_lists for x in b]


# Utility function to get agent wake up times to follow a U-quadratic distribution.
def get_wake_time(open_time, close_time, a=0, b=1):
    """Draw a time U-quadratically distributed between open_time and close_time.
    For details on U-quadtratic distribution see https://en.wikipedia.org/wiki/U-quadratic_distribution
    """

    def cubic_pow(n):
        """Helper function: returns *real* cube root of a float"""
        if n < 0:
            return -((-n) ** (1.0 / 3.0))
        else:
            return n ** (1.0 / 3.0)

    #  Use inverse transform sampling to obtain variable sampled from U-quadratic
    def u_quadratic_inverse_cdf(y):
        alpha = 12 / ((b - a) ** 3)
        beta = (b + a) / 2
        result = cubic_pow((3 / alpha) * y - (beta - a) ** 3) + beta
        return result

    uniform_0_1 = np.random.rand()
    random_multiplier = u_quadratic_inverse_cdf(uniform_0_1)
    wake_time = open_time + random_multiplier * (close_time - open_time)

    return wake_time


def numeric(s):
    """Returns numeric type from string, stripping commas from the right.
    Adapted from https://stackoverflow.com/a/379966."""
    s = s.rstrip(",")
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def get_value_from_timestamp(s, ts):
    """Get the value of s corresponding to closest datetime to ts.

    :param s: pandas Series with pd.DatetimeIndex
    :type s: pd.Series
    :param ts: timestamp at which to retrieve data
    :type ts: pd.Timestamp

    """

    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    s = s.loc[~s.index.duplicated(keep="last")]
    locs = s.index.get_loc(ts_str, method="nearest")
    out = (
        s[locs][0]
        if (isinstance(s[locs], np.ndarray) or isinstance(s[locs], pd.Series))
        else s[locs]
    )

    return out


@contextmanager
def ignored(warning_str, *exceptions):
    """Context manager that wraps the code block in a try except statement, catching specified exceptions and printing
    warning supplied by user.

    :param warning_str: Warning statement printed when exception encountered
    :param exceptions: an exception type, e.g. ValueError

    https://stackoverflow.com/a/15573313
    """
    try:
        yield
    except exceptions:
        warnings.warn(warning_str, UserWarning, stacklevel=1)
        if not silent_mode:
            print(warning_str)


def generate_uniform_random_pairwise_dist_on_line(
    left, right, num_points, random_state=None
):
    """Uniformly generate points on an interval, and return numpy array of pairwise distances between points.

    :param left: left endpoint of interval
    :param right: right endpoint of interval
    :param num_points: number of points to use
    :param random_state: np.RandomState object


    :return:
    """

    x_coords = random_state.uniform(low=left, high=right, size=num_points)
    x_coords = x_coords.reshape((x_coords.size, 1))
    out = pdist(x_coords, "euclidean")
    return squareform(out)


def meters_to_light_ns(x):
    """Converts x in units of meters to light nanoseconds

    :param x:
    :return:
    """
    x_lns = x / 299792458e-9
    x_lns = x_lns.astype(int)
    return x_lns


def validate_window_size(s):
    """Check if s is integer or string 'adaptive'."""
    try:
        return int(s)
    except ValueError:
        if s.lower() == "adaptive":
            return s.lower()
        else:
            raise ValueError(f'String {s} must be integer or string "adaptive".')


def sigmoid(x, beta):
    """Numerically stable sigmoid function.
    Adapted from https://timvieira.github.io/blog/post/2014/02/11/exp-normalize-trick/"
    """
    if x >= 0:
        z = np.exp(-beta * x)
        return 1 / (1 + z)
    else:
        # if x is less than zero then z will be small, denom can't be
        # zero because it's 1+z.
        z = np.exp(beta * x)
        return z / (1 + z)


_CITY_DISTRIBUTION: List[Tuple[float, float, float]] = [
    (39.9042, 116.4074, 21.5),  # Beijing
    (31.2304, 121.4737, 24.3),  # Shanghai
    (23.1291, 113.2644, 18.7),  # Guangzhou
    (22.5431, 114.0579, 17.5),  # Shenzhen
    (30.5728, 104.0668, 16.3),  # Chengdu
    (29.5630, 106.5516, 31.0),  # Chongqing (municipality)
    (39.3434, 117.3616, 13.9),  # Tianjin
    (30.5928, 114.3055, 12.3),  # Wuhan
    (34.3416, 108.9398, 12.0),  # Xi'an
    (30.2741, 120.1551, 12.2),  # Hangzhou
    (32.0603, 118.7969, 9.6),   # Nanjing
    (31.2989, 120.5853, 10.7),  # Suzhou
    (34.7466, 113.6254, 10.3),  # Zhengzhou
    (28.2282, 112.9388, 8.4),   # Changsha
    (41.8057, 123.4315, 8.3),   # Shenyang
    (45.8038, 126.5349, 9.5),   # Harbin
    (36.0671, 120.3826, 9.0),   # Qingdao
    (36.6500, 117.1201, 9.2),   # Jinan
    (31.8206, 117.2272, 8.2),   # Hefei
    (26.0745, 119.2965, 7.9),   # Fuzhou
    (24.4798, 118.0894, 5.1),   # Xiamen
    (25.0389, 102.7183, 6.6),   # Kunming
    (43.8256, 87.6168, 4.0),    # Urumqi
]


def random_china_location(seed: Optional[int] = None) -> Tuple[float, float]:
    """Sample a latitude/longitude pair within China, weighted by major population centers.

    The distribution is approximated by selecting from a list of major cities using their
    metropolitan populations as weights, then applying a small Gaussian perturbation. The
    result is clamped to China's approximate geographic bounding box.
    """

    rng = random.Random(seed) if seed is not None else random
    weights = [entry[2] for entry in _CITY_DISTRIBUTION]
    lat, lon, _ = rng.choices(_CITY_DISTRIBUTION, weights=weights, k=1)[0]
    lat = rng.gauss(lat, 0.5)
    lon = rng.gauss(lon, 0.5)
    lat = min(max(lat, 18.0), 53.5)
    lon = min(max(lon, 73.0), 134.5)
    return (round(float(lat), 6), round(float(lon), 6))


def network_latency_ms(
    location_a: Optional[Iterable[float]],
    location_b: Optional[Iterable[float]],
    *,
    speed_km_per_ms: float = 200.0,
    jitter_std: float = 0.15,
    minimum_ms: float = 0.05,
) -> float:
    """Estimate signal latency between two geographic coordinates in milliseconds.

    Parameters
    ----------
    location_a, location_b : iterable of float
        Latitude/longitude pairs in degrees. If either is missing, returns 0.
    speed_km_per_ms : float
        Effective propagation speed (default approximates fibre at ~200,000 km/s).
    jitter_std : float
        Standard deviation of Gaussian noise applied to the latency (ms).
    minimum_ms : float
        Lower bound to avoid zero/negative delays.
    """

    if location_a is None or location_b is None:
        return 0.0
    try:
        lat1_deg, lon1_deg = location_a
        lat2_deg, lon2_deg = location_b
    except Exception:
        return 0.0

    lat1 = math.radians(float(lat1_deg))
    lon1 = math.radians(float(lon1_deg))
    lat2 = math.radians(float(lat2_deg))
    lon2 = math.radians(float(lon2_deg))

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    earth_radius_km = 6371.0
    distance_km = earth_radius_km * c

    if speed_km_per_ms <= 0:
        base_delay = 0.0
    else:
        base_delay = distance_km / float(speed_km_per_ms)

    jitter = random.gauss(0.0, jitter_std) if jitter_std > 0 else 0.0
    delay = max(minimum_ms, base_delay + jitter)
    return float(delay)
