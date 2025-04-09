## Message

Message 目前的实现是基于字典传递消息，但是考虑到所有的消息都在同一个进程中被调用，直接调用Message的对象会更快一些，在处理消息时也可以使用Message类自带的方法，也会更加方便。

## 设计

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
 

