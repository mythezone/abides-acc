import argparse
import importlib
import sys
import time 

# #debug---1
# from rich import print 
# from rich.pretty import pprint
# #debug---2
# # import pudb 

# # pudb.set_trace()

# line_exec_count = {}
# line_exec_time = {}

# def trace_lines(frame, event, arg):
#     if event != "line":
#         return trace_lines
    
#     lineno = frame.f_lineno
#     filename = frame.f_code.co_filename
    
#     if filename not in line_exec_count:
#         line_exec_count[filename] = {}
#         line_exec_time[filename] = {}

#     if lineno not in line_exec_count[filename]:
#         line_exec_count[filename][lineno] = 0
#         line_exec_time[filename][lineno] = 0.0

#     line_exec_count[filename][lineno] += 1

#     start_time = time.time()
#     result = trace_lines
#     end_time = time.time()

#     line_exec_time[filename][lineno] += (end_time - start_time)
    
#     return result

# sys.settrace(trace_lines)


if __name__ == '__main__':

  # Print system banner.
  system_name = "ABIDES: Agent-Based Interactive Discrete Event Simulation"

  print ("=" * len(system_name))
  print (system_name)
  print ("=" * len(system_name))
  print ()

  # Test command line parameters.  Only peel off the config file.
  # Anything else should be left FOR the config file to consume as agent
  # or experiment parameterization.
  parser = argparse.ArgumentParser(description='Simulation configuration.')
  parser.add_argument('-c', '--config', required=True,
                      help='Name of config file to execute')
  parser.add_argument('--config-help', action='store_true',
                    help='Print argument options for the specific config file.')

  args, config_args = parser.parse_known_args()

  # First parameter supplied is config file.
  config_file = args.config

  config = importlib.import_module('config.{}'.format(config_file),
                                   package=None)


#   sys.settrace(None)

#   def save_trace_report(output_file="insight/logs/trace_report.txt"):
#     # 计算每个文件的总运行时间（仅包括时间 >= 0.1 的行）
#     file_exec_summary = []
#     for filename, line_times in line_exec_time.items():
#         total_time = sum(t for t in line_times.values() if t >= 0.1)
#         file_exec_summary.append((filename, total_time))
    
#     # 按总运行时间从大到小排序
#     file_exec_summary.sort(key=lambda x: x[1], reverse=True)

#     with open(output_file, "w") as f:
#         for filename, total_time in file_exec_summary:
#             f.write(f"File: {filename} (Total time: {total_time:.8f} sec)\n")
#             lines = line_exec_count[filename]
#             times = line_exec_time[filename]
#             # 只输出时间 >= 0.1 秒的行
#             for lineno in sorted(lines):
#                 exec_time = times[lineno]
#                 if exec_time >= 0.1:
#                     count = lines[lineno]
#                     f.write(f"  Line {lineno}: executed {count} times, time {exec_time:.8f} sec\n")
#             f.write("\n")
            
# save_trace_report("insight/logs/trace_report.txt")

