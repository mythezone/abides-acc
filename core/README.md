## `Kernel` 优化
1. 单例化：`Kernel`改为使用单例实现，初始化`Agent`时，不再需要显式传入`Kernel`对象，而是在使用时可以自动获取该对象。
2. 不再使用`current_time`作为模拟时钟，而是使用`Clock`类来管理时间。这样可以保证时间的唯一性和线程安全。并重新实现了记录真实时间的方法。

### `runner`方法优化
1. 参数优化：
    1. 由于模拟系统的`Agents`已经是一个可追踪的类，并且可以全局获取，不再需要agents参数
    2. 由于原ABIDES虽然在代码中加入了`num_simulations`参数表示模拟轮数，但是实际上只是用for循环进行单进程模拟，因此，该参数实际上并没有效果，不如删除，多次模拟用多次调用的方法实现。因为一个`Kernel`应该是对一组参数的模拟。而大量模拟应该使用`Simulator`类来实现。
    3. 删除了`the_seed`属性，在




## `Message`类

Message 目前的实现是基于字典传递消息，但是考虑到所有的消息都在同一个进程中被调用，直接调用Message的对象会更快一些，在处理消息时也可以使用Message类自带的方法，也会更加方便。

### 设计

0. Message的类中应该包含的静态属性和方法：
    - 静态属性：
        - `message_list`: 消息字典，存储所有的消息对象
    - 静态方法：
        - `get_message_by_id(message_id)`: 根据消息ID获取消息对象 


1. Message的对象属性应该包含：
    - `message_type`: 消息类型
        - `WAKEUP`: 唤醒消息
        
    - `content`: 消息数据
    - `sender`: 消息发送者，这里可以是一个Agent对象，也可以是指代这个Agent的id字符串。
    - `recipient`: 消息接收者
    - `time`: 消息时间
    - `id`: 消息ID
    - `status`: 消息状态，默认值为0，表示未处理，1表示已处理


## `Symbol`类
原`ABIDES`的`symbol`实现是一个字典，包含以下参数：

```python
symbol = {  'r_bar': 1e5, 
            'kappa': 1.67e-12,
            'agent_kappa': 1.67e-15,
            'sigma_s': 0,
            'fund_vol': 1e-8,
            'megashock_lambda_a': 2.77778e-13,
            'megashock_mean': 1e3,
            'megashock_var': 5e4,
            'random_state': np.random.RandomState(0),
        }
```
1. 考虑到如果要模拟整个证券交易市场，我们需要更灵活的获取这组参数，因此将其改造为一个`Tractable`类，可以通过类名直接获取对应symbol的参数。
2. 通过重载类方法`__class_getitem__`，可以通过`Symbol['AAPL']`的方式获取对应的symbol参数。


## `Exchange`类
原`ABIDES`的`Exchange`类是一个`Agent`的子类，考虑到其作为一个交易所的功能，应该是一个独立的模块，因此将其改为一个独立的类，并且将其放置在core模块下。
1. 完全重写`Exchange`类，其作为`Singleton`类的子类，其他类可以直接获取该对象的实例并调用。


## `RandomState`类
将`RandomState`类改为一个单例类，所有的随机数生成都通过该类来实现。这样可以保证每次运行的随机数都是相同的，方便调试和测试。不再需要在初始化时传入`random_state`参数。


## `Clock`类
将`Clock`类改为一个单例类，所有的时间相关操作都通过该类来实现。这样可以保证每次运行的时间都是相同的，方便调试和测试。时钟是线程安全的，因此只能通过同一个线程来调用，保证了模拟中时间的唯一性。
1. 重新封装了`now`,`reset`,`tick`,`get_forward`方法，对应提供了获取当前时间、重置时间、推进时间和获取未来时间的方法。















