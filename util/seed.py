# seed_utils.py
import os
import random
import numpy as np

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

_SEED_ALREADY_SET = False
_CURRENT_SEED = None


def seed_everything(seed: int):
    global _SEED_ALREADY_SET, _CURRENT_SEED

    if _SEED_ALREADY_SET:
        print(f"[seed_utils] Warning: Seed already set to {_CURRENT_SEED}, skipping.")
        return

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    if TORCH_AVAILABLE:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    _SEED_ALREADY_SET = True
    _CURRENT_SEED = seed
    print(f"[seed_utils] Seed set to {seed}")
