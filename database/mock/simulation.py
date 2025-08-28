import redis
import json
import random
import time
from datetime import datetime, timedelta

# 初始化 Redis 连接
r = redis.Redis(host="localhost", port=6379, db=0)

# 模拟的股票代码
MOCK_SYMBOLS = ["000001", "000002", "000004", "000006", "000007"]

# 新增：全局成交队列
TRADE_QUEUES = {symbol: [] for symbol in MOCK_SYMBOLS}
SIM_START = datetime.now()


def clear_redis_keys():
    r.delete("current_operation", "simulation_progress", "lob_snapshot:000001")
    r.delete("current_time")
    for key in r.scan_iter("market_table:*"):
        r.delete(key)
    for key in r.scan_iter("agent_status:*"):
        r.delete(key)
    for key in r.scan_iter("trade_list:*"):
        r.delete(key)


def generate_mock_market_table():
    data = {}
    for symbol in MOCK_SYMBOLS:
        open_price = round(random.uniform(10, 100), 2)
        high_price = round(open_price + random.uniform(0, 5), 2)
        low_price = round(open_price - random.uniform(0, 5), 2)
        close_price = round(random.uniform(low_price, high_price), 2)
        volume = random.randint(1000, 100000)
        amount = round(volume * close_price, 2)
        data[symbol] = {
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
            "turnover": amount,
        }
    r.hset("market_table", mapping={k: json.dumps(v) for k, v in data.items()})


def generate_mock_agent_status():
    data = {}
    for i in range(50):
        agent_id = f"agent_{i}"
        status = random.choice(["sleep", "wakeup"])
        holdings = {symbol: random.randint(0, 500) for symbol in MOCK_SYMBOLS}
        cash = round(random.uniform(1000, 100000), 2)
        pnl = round(random.normalvariate(0, 100), 2)
        portfolio = {"holdings": holdings, "cash": cash, "pnl": pnl}
        data[agent_id] = json.dumps({"status": status, "portfolio": portfolio})
    r.hset("agent_status", mapping=data)


def generate_mock_trades_and_time(step):
    """每次对每个symbol随机生成成交列表，并记录模拟时间"""
    agent_count = 200
    now = SIM_START + timedelta(milliseconds=step * 800)  # 速度可以调
    now_ts = int(now.timestamp() * 1000)
    r.set("current_time", now_ts)
    for symbol in MOCK_SYMBOLS:
        queue = TRADE_QUEUES[symbol]
        r.delete(f"trade_list:{symbol}")  # 清空旧记录
        queue.clear()
        # 本次生成1~3条
        for _ in range(random.randint(1, 3)):
            t = now + timedelta(milliseconds=random.randint(0, 400))
            agent1 = f"agent_{random.randint(0, agent_count - 1)}"
            agent2 = f"agent_{random.randint(0, agent_count - 1)}"
            price = round(random.uniform(10, 100), 2)
            volume = random.randint(1, 500)
            trade = {
                "time": int(t.timestamp() * 1000),
                "agent1": agent1,
                "agent2": agent2,
                "price": price,
                "volume": volume,
                "symbol": symbol,
            }
            queue.append(trade)
            # 使用 Redis 原生 List 操作写入
            r.rpush(f"trade_list:{symbol}", json.dumps(trade))
            r.ltrim(f"trade_list:{symbol}", -10, -1)


def generate_mock_operation_and_progress(step: int):
    operation = f"Executing simulation step {step}"
    progress = round(min(1.0, step / 100), 2)
    r.set("current_operation", operation)
    r.set("simulation_progress", progress)


def generate_mock_lob_snapshot():
    for symbol in MOCK_SYMBOLS:
        bids = [(round(10 - 0.1 * i, 2), random.randint(10, 100)) for i in range(5)]
        asks = [(round(10 + 0.1 * i, 2), random.randint(10, 100)) for i in range(5)]
        lob_data = {"bid": bids, "ask": asks}
        r.set(f"lob_snapshot:{symbol}", json.dumps(lob_data))


def run_mock_simulation():
    clear_redis_keys()
    step = 0
    while True:
        generate_mock_market_table()
        generate_mock_agent_status()
        generate_mock_operation_and_progress(step)
        generate_mock_lob_snapshot()
        generate_mock_trades_and_time(step)

        print(f"[Mock] Step {step} - Data refreshed")
        step += 1
        time.sleep(1)  # 每秒刷新一次


if __name__ == "__main__":
    run_mock_simulation()
