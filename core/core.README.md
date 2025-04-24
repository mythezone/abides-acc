## `Kernel` 优化
1. 单例化：`Kernel`改为使用单例实现，初始化`Agent`时，不再需要显式传入`Kernel`对象，而是在使用时可以自动获取该对象。
2. 不再使用`current_time`作为模拟时钟，而是使用`Clock`类来管理时间。这样可以保证时间的唯一性和线程安全。并重新实现了记录真实时间的方法。
3. 方法优化：
    1. `fmtTime()`方法由于已经改为直接返回其参数，而不是格式化的时间因此该方法本省没有必要，已经删除。
### `runner`方法优化
1. 参数优化：
    1. 由于模拟系统的`Agents`已经是一个可追踪的类，并且可以全局获取，不再需要agents参数
    2. 由于原ABIDES虽然在代码中加入了`num_simulations`参数表示模拟轮数，但是实际上只是用for循环进行单进程模拟，因此，该参数实际上并没有效果，不如删除，多次模拟用多次调用的方法实现。因为一个`Kernel`应该是对一组参数的模拟。而大量模拟应该使用`Simulator`类来实现。
    3. 删除了`the_seed`属性，在

2. 流程优化
    1. 不再需要对Agent列表进行初始化，删除了对应的代码。
    2. 由`kernel`通过`messages`这个优先队列来掌控时间的进行，每次取出优先队列中第一个消息，并将仿真时间推进至该消息的到达时间，这种消息处理方式更高效，每个发送至`kernel`的消息都只会被`kernel`和`Agent`各处理一次，并且保证了`Agent`不会收到未来的消息。
        - 如果该消息是由`exchange`接收，就调用`exchange`的`message_handler`方法进行处理。
        - 如果消息是普通`Agent`接收，分为两种情况，一种是普通信息，直接发送至该`Agent`的`inbox`，另一种是唤醒信息，直接将对应的Agent唤醒，并处理其`inbox`中的所有消息，如果需要发送消息则需要计算消息的累计延时（比如发送多条消息，每条消息的送达时间会有不同的延时）。





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

2. 方法修改：
    - 修改`__lt__`方法，对只使用接收时间对消息进行排序，接收时间越小的越靠前
    - 修改`__eq__`方法，只有id相同的消息才是相同的消息
    - 基于以上两个方法，用`@total_ordering`装饰器补全方法的所有比较方法。
    - `__str__`方法待修改


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
- 总体变化
    - 原`ABIDES`的`Exchange`类是一个`Agent`的子类，考虑到其作为一个交易所的功能，应该是一个独立的模块，因此将其改为一个独立的类，并且将其放置在core模块下。
    - 完全重写`Exchange`类，其作为`Singleton`类的子类，其他类可以直接获取该对象的实例并调用。
    - `Exchange`类原来使用`reciveMessage`方法，用`if-elif-else`方法进行分支判断和消息处理，现在改为使用更加优雅的字典映射方法，使用`message_type`作为键，消息处理函数作为值，直接调用对应的函数进行处理。
- 删除方法：
    - `getMarketClose`
    - `getMarketOpen`
    - `sendMessage`

- 重新实现：
    - `logOrderBookSnapshots`




## `RandomState`类
将`RandomState`类改为一个单例类，所有的随机数生成都通过该类来实现。这样可以保证每次运行的随机数都是相同的，方便调试和测试。不再需要在初始化时传入`random_state`参数。


## `Clock`类
将`Clock`类改为一个单例类，所有的时间相关操作都通过该类来实现。这样可以保证每次运行的时间都是相同的，方便调试和测试。时钟是线程安全的，因此只能通过同一个线程来调用，保证了模拟中时间的唯一性。
1. 重新封装了`now`,`reset`,`tick`,`get_forward`方法，对应提供了获取当前时间、重置时间、推进时间和获取未来时间的方法。


## `Logger`类
针对ABIDES重新封装了python自带的`logging`模块，更好的记录在仿真过程中的日志信息。


## `OrderBook`类
- 总体变化：
    - `OrderBook`类从`order`模块移动至`core`模块下，作为一个独立的类，提供了对订单簿的操作。
    - `OrderBook`提供全局获取接口，在`kernel`中初始化，对每个`symbol`都初始化一个对应的`OrderBook`对象。
- 方法变化：
    - 删除：
        - `kernelInitializing`
        - `kernelTerminating`

    - 重写：




















