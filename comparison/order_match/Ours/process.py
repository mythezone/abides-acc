import pandas as pd

INPUT_PATH = "comparison/order_match/Ours/raw_log_1s/SZ000001/lob.csv"
OUTPUT_PATH = "comparison/order_match/Ours/raw_log_1s/SZ000001/processed_lob.csv"
MAX_ROWS = 3600

FIELDS = ["time", "bestBidPrice", "bestAskPrice", "bestBidVolume", "bestAskVolume"]

df = pd.read_csv(INPUT_PATH)
df = df.head(MAX_ROWS)

out_df = pd.DataFrame(
    {
        "time": [float(i + 1) for i in range(len(df))],
        "bestBidPrice": df["BidPrice0"],
        "bestAskPrice": df["AskPrice0"],
        "bestBidVolume": df["BidVolume0"].apply(
            lambda x: f"{float(x):.6f}" if pd.notnull(x) and x != "" else ""
        ),
        "bestAskVolume": df["AskVolume0"].apply(
            lambda x: f"{float(x):.6f}" if pd.notnull(x) and x != "" else ""
        ),
    }
)

out_df.to_csv(OUTPUT_PATH, index=False)
