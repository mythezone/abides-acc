# ABIDES-ACC: Acceleration of ABIDES for Financial Calibration
[![License](https://img.shields.io/github/license/mythezone/abides-acc.svg)](https://github.com/mythezone/abides-acc/blob/main/LICENSE)

## 主要优化
1. 对于所有类和方法的参数都使用typing进行注释，增加了代码的可读性和规范性。
2. 重写了`Message`类，让消息的传递、查询和处理更为高效。将`message`模块移动至`core`模块下。
3. 重写了`Agent`类，增加了对消息的处理和查询方法。
4. 重写了`Kernel`类，将其放置在`core`模块下，让代码结构更具有逻辑性，修改了kernel的部分实现方式。
5. 添加了`Simulation`类
6. 添加了`Market`类
7. 重写了`Order`类
8. 添加了GUI模块，提供了Web界面进行可视化运行。
9. 为每个重构/修改的类添加了单元测试，确保代码的正确性和稳定性。
10. `Order`作为模拟中的主要组成之一，应该具有独立的模块。将`util.order`模块提升到主模块`order`，中，并且将`Order`相关的类也放到`order`模块中，比如`OrderBook`，`OrderManager`等。
11. 重新实现`Exchange`类，由于每次模拟都只有一个交易所，其作为`Agent`的子类似乎并不合适，大多数的模拟器功能都要通过该对象实现，因此将其改写后放在`core`模块下，
12. 按照PEP8规范[1]将整个仓库中的代码变得更`pythonic`的
    1. 将所有模块名改为小写，类名改为大写，方法名改为小写加下划线。
    2. 所有的缩进修改为4个空格
    3. 大段的方法注释改为`"""`的形式
13. 将python的支持版本提升到3.12 (Pandas的几个函数在3.12中有了新的实现方式，使用了新的语法糖，提升了代码的可读性和性能，但是可能会不兼容3.9及以下版本)




## Quickstart
```bash
mkdir project
cd project

git clone https://github.com/mythezone/abides-acc.git
cd abides-acc
pip install -r requirements.txt
```

## Acknowledgements

This project builds upon [![GitHub stars](https://img.shields.io/github/stars/abides-sim/abides.svg?style=social)](https://github.com/abides-sim/abides/stargazers), an excellent agent-based market simulator.

## References
[1] [PEP8规范](https://peps.python.org/pep-0008/)