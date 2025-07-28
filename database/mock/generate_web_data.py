import random
import time


def gen_kline_series(start_price, n, interval=60 * 60 * 4, start_ts=None):
    if not start_ts:
        now = int(time.time())
        start_ts = now - n * interval
    klines = []
    price = start_price
    for i in range(n):
        open_p = round(price + random.uniform(-0.1, 0.1), 2)
        close_p = round(open_p + random.uniform(-0.15, 0.15), 2)
        high_p = round(max(open_p, close_p) + random.uniform(0, 0.1), 2)
        low_p = round(min(open_p, close_p) - random.uniform(0, 0.1), 2)
        volume = random.randint(15000, 25000)
        ts = start_ts * 1000 + i * interval * 1000  # ms
        klines.append(
            {
                "timestamp": ts,
                "open": open_p,
                "close": close_p,
                "high": high_p,
                "low": low_p,
                "volume": volume,
            }
        )
        price = close_p
    return klines


def gen_depth(center, n_levels=3):
    bids = []
    asks = []
    for i in range(n_levels):
        bids.append(
            {"price": round(center - 0.1 * i, 2), "amount": random.randint(600, 1200)}
        )
        asks.append(
            {
                "price": round(center + 0.1 * i + 0.1, 2),
                "amount": random.randint(500, 1100),
            }
        )
    return bids, asks


def dict_to_js(obj, indent=2):
    """递归输出 JS-like 字面量，不加引号"""
    IND = " " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            lines.append(f"{IND}{k}: {dict_to_js(v, indent + 2)}")
        return "{\n" + ",\n".join(lines) + f'\n{" " * (indent-2)}}}'
    elif isinstance(obj, list):
        lines = [dict_to_js(x, indent + 2) for x in obj]
        return "[\n" + ",\n".join(lines) + f'\n{" " * (indent-2)}]'
    elif isinstance(obj, str):
        return obj  # 字符串不加引号（前端可视需要自行加引号）
    else:
        return str(obj)


def main(symbols, kline_len=4, out_file="output.txt"):
    data = {}
    for s in symbols:
        base = random.uniform(8, 16)
        real_kline = gen_kline_series(base, kline_len)
        real_last = real_kline[-1]["close"]
        sim_kline = gen_kline_series(real_last + random.uniform(-0.3, 0.3), kline_len)
        sim_last = sim_kline[-1]["close"]
        realBids, realAsks = gen_depth(real_last)
        simBids, simAsks = gen_depth(sim_last)
        data[s] = {
            "realKline": real_kline,
            "realBids": realBids,
            "realAsks": realAsks,
            "simKline": sim_kline,
            "simBids": simBids,
            "simAsks": simAsks,
        }

    # 输出格式处理
    with open(out_file, "w", encoding="utf8") as f:
        f.write("{\n")
        for sym, val in data.items():
            f.write(f"  '{sym}': {dict_to_js(val, indent=4)},\n")
        f.write("}\n")
    print(f"已写入 {out_file}")


if __name__ == "__main__":
    symbols = ["000001", "000002", "000063", "000333", "002230", "002415"]
    main(symbols, kline_len=40, out_file="simu_data.txt")
