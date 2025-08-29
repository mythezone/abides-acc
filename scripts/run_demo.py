import os
import sys
import pandas as pd

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.kernel import Kernel


def main():
    today = pd.Timestamp.now().date()
    cfg = {
        "name": "demo",
        "start_date": str(pd.Timestamp.combine(today, pd.Timestamp("09:30").time())),
        "trading_days": [str(today)],
        "exchange_type": "SZSE",
    }
    kernel = Kernel(config=cfg)
    kernel.initialize()
    kernel.init_agent(
        [
            {"type": "zero_intelligence", "num": 2, "params": {}},
        ]
    )
    result = kernel.run(max_steps=500)
    print("Demo finished:", result)


if __name__ == "__main__":
    main()
