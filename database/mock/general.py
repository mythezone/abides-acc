from core.const import *
from database.smb_client import SambaClient as SC
from database.redis_client import RedisClient as RC

sc = SC()
rc = RC()


sample_remote_folder = f"{SAMPLE_FOLDER}/{SAMPLE_FILE}"
files = sc.get_files_in_folder(SAMPLE_FOLDER)
# print("Files in folder:", files)

res = set()

for f in files:
    if "SZ1" in f:
        stock = f.split(".")[0]
        res.add(stock)


rc.update_data("stocks", ",".join(res))
print("Updated stocks in Redis:", res)

f = rc.get_data("stocks")
if f:
    print("Stocks in Redis:", f)
else:
    print("No stocks found in Redis.")
