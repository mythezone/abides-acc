import re

def parse_log_file(input_file, output_file):
    file_times = {}
    
    with open(input_file, 'r') as f:
        current_file = None
        
        for line in f:
            file_match = re.match(r'File: (.+)', line)
            line_match = re.match(r'Line \d+: executed \d+ times, time ([\d\.]+) sec', line)
            
            if file_match:
                current_file = file_match.group(1)
                file_times[current_file] = 0.0
            elif line_match and current_file:
                file_times[current_file] += float(line_match.group(1))
    
    sorted_files = sorted(file_times.items(), key=lambda x: x[1], reverse=True)
    
    with open(output_file, 'w') as out_f:
        for file, total_time in sorted_files:
            out_f.write(f"{file}: total execution time {total_time:.8f} sec\n")
    
    print("Log processing complete. Results saved to", output_file)


# 使用示例
input_log = "exp-optimized-1.log"  # 输入的日志文件名
output_log = "sum-optimized-1.log"   # 输出的统计结果文件名
parse_log_file(input_log, output_log)
