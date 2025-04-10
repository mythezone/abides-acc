## Order及Order相关类的改动

### 改动概览

1. 将`Order`类及`Order`相关的类移动至`order`模块
2. 将`Order`类放置在`order.base`模块中
3. 重写`LimitOrder`类的实现方式
    1. 重写`LimitOrder`类全序的判断方法，因为`LimitOrder`的大小实际上与`LimitOrder`的创建先时间（也就是`id`属性的大小没有直接关系，而是与`LimitOrder`的方向（买或者卖）、价格以及提交至`Exchange`的时间有关。因此全序关系应该是先价格后时间（理论上不存在两个相同id的情况，如果考虑到这个可以将id也放到全序关系中）。
    2. 买方的`LimitOrder`是从大到小优先排序，在实现时，如果`LimitOrder`的方向时买方，即`is_buy_order`为`True`是，在对比时，就将`LimitOrder`的价格取反，这样就可以实现买方的`LimitOrder`是从大到小优先排序了。 
    3. 为了实现高速对比，我们按照PEP8规范，用`from functools import total_ordering`，补全了全序。
    
    
4. 删除`Order`类中的`__copy__`和`__deepcopy__`方法
    1. 重新实现的`Order`不需要进行copy。
    2. `Order`类及其子类需要重载`__eq__`和`__lt__`方法。

5. 重新实现`OrderBook`类
    1. `OrderBook`实际在运行时无需记录价格档位，因为只有最优先的对手订单才会被交易，如果一张订单没有吃完所有对手订单，则更新对手订单簿之后再继续交易即可。因此，买卖双方的订单都可以用一个优先队列来实现。
    



