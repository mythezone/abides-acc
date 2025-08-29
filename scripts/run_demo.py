import os
import sys
import pandas as pd

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.kernel import Kernel


def main():
    cfg_path = os.environ.get("SIM_CONFIG", os.path.join(os.path.dirname(__file__), "..", "config", "test.json"))
    kernel = Kernel.from_config(cfg_path)
    result = kernel.run(max_steps=1000)
    print("Demo finished:", result)


if __name__ == "__main__":
    main()
