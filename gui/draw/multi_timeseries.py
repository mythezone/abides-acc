import matplotlib.pyplot as plt


def plot_multi_timeseries(data, title=None, xlabel=None, ylabel=None, legend=None):
    """
    Plot multiple time series on the same graph.

    Parameters:
    - data: A dictionary where keys are labels and values are lists of y-values.
    - title: Title of the plot.
    - xlabel: Label for the x-axis.
    - ylabel: Label for the y-axis.
    - legend: List of labels for the legend.

    Returns:
    - None
    """

    plt.figure(figsize=(10, 6))

    for xs in data:
        plt.plot(xs)

    if title:
        plt.title(title)

    if xlabel:
        plt.xlabel(xlabel)

    if ylabel:
        plt.ylabel(ylabel)

    if legend:
        plt.legend(legend)

    plt.grid()
    plt.show()


def plot_x_y(x, y, title=None, xlabel=None, ylabel=None, legend=None):
    """
    Plot multiple time series on the same graph.

    Parameters:
    - data: A dictionary where keys are labels and values are lists of y-values.
    - title: Title of the plot.
    - xlabel: Label for the x-axis.
    - ylabel: Label for the y-axis.
    - legend: List of labels for the legend.

    Returns:
    - None
    """

    plt.figure(figsize=(10, 6))

    plt.plot(x, y)

    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if legend:
        plt.legend(legend)
    plt.grid()
    plt.show()
