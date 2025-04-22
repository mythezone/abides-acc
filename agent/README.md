## `Agent` 类

### 重写Agent的基础类
1. `Agent`类现在继承自`Trackable`类，使得所有的`Agent`对象都可以追溯。
2. 属性修改：
    1. `Agent`类现在不需要`name`作为初始化参数，在原本的实现中，该名称实际上就是其索引。在修改后的实现中，使用id直接取代了名称。
    2. `Agent`的`id`现在由`Trackable`父类自动初始化和管理，并可以直接通过`Agent[id]`的方式获取对应的`Agent`对象。
    3. 防止时间变量名混淆，将agent的`currentTime`改为`agent_current_time`,类型是`pd.Timestamp`，表示agent认为自己当前所处的时间。
    4. 参照`PEP8`标准，将初始化参数的`type`改为`type_`，并且Agent的`type_`属性实际上就是Agent的类名，可以不显式的指定，而是直接通过Agent的类名确定。而Agent的name则由类名+id构成，也无需显示指定，因此在初始化参数中删除了这一项。
    5. `Agent`类现在包含一个待处理的消息队列，

3. 方法修改：
    - `sendMessage`方法，修改为`send`方法（该方法不仅发送消息，也发送订单等，因此不应该单纯叫做`send_message`），该方法直接创建一个`Message`对象，并将其直接添加到`Kernel`的消息列表中。
    - `message`构造时，只有发送的时间戳，发送时间戳包含了Agent处理消息的计算延时，在调用`Kernel`的`add_message`方法是，需要计算消息的到达延时，并以到达延时作为消息的排序依据。


3. 方法修改：
    1. 由于现在的`kernel`已经可以从全局访问，因此无需显示定义`kernelInitializing`方法，已删除。
    2. Agent在初始化时需要指定Agent的当前时间，而不是等待`kernel`初始化后再通过`kernel`指定。




### 删除`FinancialAgent`类
FinancialAgent相比Agent基类，仅多提供了一条`dollize`方法，将整数的分（集市场中的最小tick）转换为两位小数的元，这一过程应该体现在最后的log的handler中，而不是在Agent中实现。

