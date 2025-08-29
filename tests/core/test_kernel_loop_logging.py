import os
import json
import pandas as pd

from core.kernel import Kernel


def test_kernel_loop_and_logging(tmp_path):
    cfg = {
        "simulation": {
            "start_date": str(pd.Timestamp.now().date()),
            "end_date": str(pd.Timestamp.now().date()),
            "exchange_type": "SZSE",
        },
        "kernel": {
            "name": "UnitTestRun",
            "agents": [
                {"type": "zero_intelligence", "num": 1, "params": {}},
            ],
        },
        "symbols": ["000001", "000002"],
    }
    cfg_file = tmp_path / "cfg.json"
    with open(cfg_file, "w") as f:
        json.dump(cfg, f)

    kernel = Kernel.from_config(str(cfg_file))
    res = kernel.run(max_steps=200)
    assert res["processed"] > 0

    log_dir = os.path.join("log", cfg["kernel"]["name"]) \
        if not os.path.isabs(kernel.config.get("log_dir", "")) else kernel.config["log_dir"]
    log_file = os.path.join(log_dir, "log.csv")
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        content = f.read()
    assert "SEND" in content
    assert "RECV" in content
    assert "PROC" in content

