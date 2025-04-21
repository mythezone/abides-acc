## 添加`tests`模块
使用目前最流行的python测试框架`pytest`，对所有的模块进行单元测试，确保代码的正确性和稳定性。


### `tests`模块的使用规则
1. 所有重构的类都需要有对应的测试类，测试类放在tests文件夹中的对应的模块下。
2. 测试模块的命名规则为`test_modulename.py`，其中`modulename`为模块名。
3. 测试类的命名为`TestModulename`，其中`Modulename`为待测试的类名。
4. 测试方法的命名为`test_methodname`，其中`methodname`为待测试的方法名。