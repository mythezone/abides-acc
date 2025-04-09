# ABIDES-ACC: Acceleration of ABIDES for Financial Calibration
[![License](https://img.shields.io/github/license/mythezone/abides-acc.svg)](https://github.com/mythezone/abides-acc/blob/main/LICENSE)

## 主要优化
1. 对于所有类和方法的参数都使用typing进行注释，增加了代码的可读性和规范性。
2. 重写了`Message`类，让消息的传递、查询和处理更为高效。
3. 重写了`Agent`类，增加了对消息的处理和查询方法。
4. 重写了`Kernel`类，将其放置在`core`模块下，让代码结构更具有逻辑性，修改了kernel的部分实现方式。
5. 添加了`Simulation`类
6. 添加了`Market`类
7. 重写了`Order`类
8. 添加了GUI模块，提供了Web界面进行可视化运行。
9. 为每个重构/修改的类添加了单元测试，确保代码的正确性和稳定性。
10. `Order`作为模拟中的主要组成之一，应该具有独立的模块。将`util.order`模块提升到主模块`order`，中，并且将`Order`相关的类也放到`order`模块中，比如`OrderBook`，`OrderManager`等。



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