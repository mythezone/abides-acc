import argparse
import importlib
import sys
import time 

#debug---1
from rich import print 
from rich.pretty import pprint
#debug---2
# import pudb 

# pudb.set_trace()

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

#   # 输出执行次数和时间
#   for filename, line_counts in line_exec_count.items():
#       print(f"File: {filename}")
#       for lineno, count in sorted(line_counts.items()):
#           print(f"Line {lineno}: executed {count} times, time {line_exec_time[filename][lineno]:.8f} sec")