import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.kernel import Kernel


def main():
    cfg_path = os.environ.get(
        "CALIB_CONFIG",
        os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json"),
    )
    kernel = Kernel.from_config(cfg_path)
    res = kernel.run(max_steps=20000)
    print("Calibration finished:", res)


if __name__ == "__main__":
    main()

