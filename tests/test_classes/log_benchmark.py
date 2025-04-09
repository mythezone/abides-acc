import time
import os
from util.logger import ProcessLogger
import datetime 
# from util.util import log_print

LOG_COUNT = 1_000_000
SYNC_LOG_FILE = "logs/direct_write.log"
ASYNC_LOG_FILE = "logs/async_process_write.log"

logger = ProcessLogger()

def log_print (msg:str, *args):
    formatted = msg.format(*args)
    logger.log(formatted)  

# 方式 1：直接写入文件（阻塞式）
def test_direct_write():
    if os.path.exists(SYNC_LOG_FILE):
        os.remove(SYNC_LOG_FILE)
    start = time.time()
    
    for i in range(LOG_COUNT):
        with open(SYNC_LOG_FILE, "a") as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            f.write(f"[SYNC] log line {i} {timestamp}")
    end = time.time()
    return end - start

# 方式 2：通过 ProcessLogger 异步写入
def test_process_logger():
    # if os.path.exists(ASYNC_LOG_FILE):
    #     os.remove(ASYNC_LOG_FILE)

    start = time.time()
    for i in range(LOG_COUNT):
        log_print("[ASYNC] log line {}",i)
    # 等待队列清空
    
    logger.shutdown()
    end = time.time()
    return end - start

def main():
    print("Writing 1,000,000 log entries...")
    
    t1 = test_direct_write()
    print(f"Direct file write: {t1:.2f} seconds")
    
    t2 = test_process_logger()
    print(f"ProcessLogger async write: {t2:.2f} seconds")

    print("\nSummary:")
    if t1 > t2:
        print(f"✅ ProcessLogger faster by {t1 - t2:.2f} seconds")
    else:
        print(f"❗️Direct write faster by {t2 - t1:.2f} seconds")

if __name__ == "__main__":
    main()