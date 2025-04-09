import re
from collections import defaultdict

total_times = defaultdict(float)

def sum_of_log(file_name,output_file_name):
    with open(file_name, 'r') as f:
        lines = f.readlines()

    for line in lines:
        match = re.match(r"^File: (.+)", line)
        if match:
            current_file = match.group(1)
        else:
            match = re.search(r"time ([\d\.]+) sec", line)
            if match and current_file:
                total_times[current_file] += float(match.group(1))

    with open(output_file_name, 'w') as f:
        f.write("\n\n# Total execution time per file:\n")
        for file, total_time in total_times.items():
            f.write(f"# {file}: {total_time:.8f} sec\n")

# 使用示例
input_log = "./insight/logs/trace_report.log"  # 输入的日志文件名
output_log = "./insight/logs/trace_report_summary.log"   # 输出的统计结果文件名

sum_of_log(input_log, output_log)

