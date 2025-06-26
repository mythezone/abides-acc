## `Agent` 类

### 重写Agent的基础类
1. `Agent`类现在继承自`Trackable`类，使得所有的`Agent`对象都可以追溯。
2. 属性修改：
    - `Agent`类现在不需要`name`作为初始化参数，在原本的实现中，该名称实际上就是其索引。在修改后的实现中，使用id直接取代了名称。
    - `Agent`的`id`现在由`Trackable`父类自动初始化和管理，并可以直接通过`Agent[id]`的方式获取对应的`Agent`对象。
    - 防止时间变量名混淆，将agent的`currentTime`改为`agent_current_time`,类型是`pd.Timestamp`，表示agent认为自己当前所处的时间。
    - 参照`PEP8`标准，将初始化参数的`type`改为`type_`，并且Agent的`type_`属性实际上就是Agent的类名，可以不显式的指定，而是直接通过Agent的类名确定。而Agent的name则由类名+id构成，也无需显示指定，因此在初始化参数中删除了这一项。
    - `Agent`类现在包含一个待处理的消息队列,`msg_inbox`，用于存储该agent尚未处理的信息，已经处理完的信息则用`logging`记录，并删除。
    - `Agent`的时间已经可以从`kernel`中获取，因此不再需要单独保存自己的当前时间。删除了`current_time`属性。
    - 由于现在的`kernel`已经可以从全局访问，因此无需显示定义`kernelInitializing`方法，已删除。
    - Agent在初始化时需要指定Agent的当前时间，而不是等待`kernel`初始化后再通过`kernel`指定。

3. 删除方法：
    - `kernelStopping`
    - `kernelTerminating`
    - `logEvent`
    - `writeLog`
    - `updateAgentState`
    - `setWakeup`
    - `setComputationDelay`
    - `reciveMessage`
    - `delay`

4. 方法修改：
    - `initiate`方法，在Agent被创建时调用，提交一条信息交给`kernel`存档，并设置下次唤醒时间。
    - `sendMessage`方法，修改为`send`方法（该方法不仅发送消息，也发送订单等，因此不应该单纯叫做`send_message`），该方法直接创建一个`Message`对象，并将其直接添加到`Kernel`的消息列表中。
    - `message`构造时，只有发送的时间戳，发送时间戳包含了Agent处理消息的计算延时，在调用`Kernel`的`add_message`方法是，需要计算消息的到达延时，并以到达延时作为消息的排序依据。
    - `reciveMessage`方法与`wakeup`方法合并了，在`Agent`被唤醒后，会依次处理其`inbox`中的所有收到的消息。
    - 重新实现`getComputationDelay`方法，改名为`get_computation_delay`返回Agent处理消息的计算延时。
    - 重新实现`setWakeup`方法，改名为`set_next_wakeup`,该方法会创建一条唤醒`Message`，并置入`kernel`的消息队列中，等待`kernel`读到该信息后唤醒。

5. 添加方法
    - `wakeup_delay`方法，返回一个大于0的整数，表示从本次唤醒到下次唤醒之间的延时（单位为纳秒）

### 删除`FinancialAgent`类
FinancialAgent相比Agent基类，仅多提供了一条`dollize`方法，将整数的分（集市场中的最小tick）转换为两位小数的元，这一过程应该体现在最后的log的handler中，而不是在Agent中实现。

### 重写`TradingAgent`类
- `TradingAgent`现在继承至`Agent`类.
- 参数修改：
    - 删除`log_orders`, `log_to_file`参数
    - 添加`kernel`参数
    - 添加`portfolio`参数，表示Agent当前的持仓。
    - 添加`cash`参数，表示Agent当前的流动资金。
- 属性修改：
    - 删除`mkt_open`,`mkt_close`,`log_orders`,`log_to_file`
    - `start_cash`改为`cash`，表示Agent当前有的流动资金。
    - 添加`portfolio`的字典，表示Agent当前的持仓。
    - 删除`MKT_BUY`,`MKT_SELL`，不再需要这两个参数。
    - 删除`exchange_ts`字典
    - 删除`first_wake`属性，初始的Log会由父类Agent的`initiate`方法实现。
    - 删除`book`属性，不再需要从`exchange`中获取`book`

- 方法修改：
    - 删除
        - `kernelStarting`
    - 修改
        - `wakeup`: 不再区分首次唤醒（已经在父类`Agent`的`initiate`方法中实现）。不再请求`mkt_open`,`mkt_close`信息。（从现实角度来看，这些都是已知的，因而可以直接从`exchange`实例中获取。
        - 修改`reciveMessage`为`message_handler`
            - 已经不需要处理`WHEM_MKT_OPEN`、`WHEM_MKT_CLOSE`、`ORDER_EXECUTED|ACCEPTED|CANCELLED`、`MKT_CLOSED|OPENED`等类型的消息了。
            - 

    - 添加

## 重写`NoiseAgent`类
- 总体修改
    - 根据其父类`TradingAgent`改写了相关的构造方法
    - 删除了不必要的属性和方法
    - 不再指定其symbol，`NoiseAgent`现在可以对所有`symbol`下单。
    - 改写了旧的`wakeup`逻辑

- 方法修改
    - `placeOrder`方法： 改为`place_order`
        - 



    
