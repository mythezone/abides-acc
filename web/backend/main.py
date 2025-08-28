from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis_client import RedisClient
from models import SymbolKlineBlock
import json

rc = RedisClient()
r = rc.get_client()

app = FastAPI()

# CORS（跨域）配置，允许前端访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 可指定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 示例API ==========
@app.get("/api/symbols")
def get_all_symbols():
    """获取所有已存的股票代码"""
    keys = r.keys("stock:*")
    symbols = [k.decode().split(":")[1] for k in keys]
    return {"symbols": symbols}


@app.get("/api/data/{symbol}")
def get_symbol_data(symbol: str):
    """获取某一股票的K线和盘口数据"""
    raw = r.get(f"stock:{symbol}")
    if not raw:
        raise HTTPException(404, f"Symbol {symbol} not found")
    # 假设保存的就是一个json字符串
    return json.loads(raw)


# ========== 示例：推送一只股票的模拟数据 ==========
@app.post("/api/data/{symbol}")
def upload_symbol_data(symbol: str, data: SymbolKlineBlock):
    """保存一只股票的行情数据到Redis"""
    r.set(f"stock:{symbol}", data.json())
    return {"ok": True}
