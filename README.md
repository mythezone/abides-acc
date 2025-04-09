# ABIDES-ACC: Acceleration of ABIDES for Financial Calibration
[![License](https://img.shields.io/github/license/mythezone/abides-acc.svg)](https://github.com/mythezone/abides-acc/blob/main/LICENSE)

## 主要优化
1. 对于所有类和方法的参数都使用typing进行注释，增加了代码的可读性和规范性。
2. 重写了`Message`类，让消息的传递、查询和处理更为高效。
3. 重写了`Agent`类，增加了对消息的处理和查询方法。
4. 重写了`Kernel`类，将其放置在`core`模块下，修改了部分运行逻辑。
5. 添加了`Simulation`类
6. 添加了`Market`类
7. 重写了`Order`类
8. 添加了GUI模块，提供了Web界面进行可视化运行。



## Quickstart
```bash
mkdir project
cd project

git clone https://github.com/mythezone/abides-acc.git
cd abides-acc
pip install -r requirements.txt
```

## Acknowledgements

This project builds upon [![GitHub stars](https://img.shields.io/github/stars/abides-sim/abides.svg?style=social)](https://github.com/abides-sim/abides/stargazers),an excellent agent-based market simulator.