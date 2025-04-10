## Kernel 优化

### 1. 单例
`Kernel`改为使用单例实现，初始化`Agent`时，不再需要显式传入`Kernel`对象，而是在使用时可以自动获取该对象。


## Message

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


## Symbol
原ABIDES的symbol实现是一个字典，包含以下参数：

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





