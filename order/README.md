## Order及Order相关类的改动

### 改动概览

1. 将`Order`类及`Order`相关的类移动至`order`模块
2. 将`Order`类放置在`order.base`模块中，重写`Order`类
    1. `Order`类现在继承自`Trackable`类，使得所有的`Order`对象都可以追溯。 
    2. 添加`history`属性，记录所有与`Order`变化有关的操作记录，比如撤单、成交（部分成交）、修改订单。
    3. 添加与订单变化相关的接口方法`deal`, `cancel`, `modify`, `finish`等。
    4. 添加组合类`Transaction`(名字待定)，用于记录所有与订单变化相关的信息。


3. 重写`LimitOrder`类的实现方式
    1. 重写`LimitOrder`类全序的判断方法，因为`LimitOrder`的大小实际上与`LimitOrder`的创建先时间（也就是`id`属性的大小没有直接关系，而是与`LimitOrder`的方向（买或者卖）、价格以及提交至`Exchange`的时间有关。因此全序关系应该是先价格后时间（理论上不存在两个相同id的情况，如果考虑到这个可以将id也放到全序关系中）。
    2. 买方的`LimitOrder`是从大到小优先排序，在实现时，如果`LimitOrder`的方向时买方，即`is_buy_order`为`True`是，在对比时，就将`LimitOrder`的价格取反，这样就可以实现买方的`LimitOrder`是从大到小优先排序了。 
    3. 为了实现高速对比，我们按照PEP8规范，用`from functools import total_ordering`，补全了全序。
    

4. 删除`Order`类中的`__copy__`和`__deepcopy__`方法
    1. 重新实现的`Order`不需要进行copy。
    2. `Order`类及其子类需要重载`__eq__`和`__lt__`方法。
    3. 在`Order`类中添加了`histories`属性，这里会记录所有与`Order`变化有关的的操作记录， 比如撤单、成交（部分成交）、修改订单。

5. 重新实现了`LimitOrder`类



6. 重新实现`OrderBook`类
    1. `OrderBook`实际在运行时无需记录价格档位，因为只有最优先的对手订单才会被交易，如果一张订单没有吃完所有对手订单，则更新对手订单簿之后再继续交易即可。因此，买卖双方的订单都可以用一个优先队列来实现。
    2. `OrderBook`添加一个`Log`方法，方法包含frequency和level两个参数，用于控制日志输出频率和记录的档位级别。
    3. 删除`OrderBook`类中的`history`属性，重新实现历史订单回溯方式。
    4. 添加`get`方法并重载了`__class_getitem__`方法，使得`OrderBook`可以通过`OrderBook[Order]`的方式获取订单簿（如果该订单簿不存在就创建一个）。
    5. 重新实现了`handle_order`方法
        - 删除了对`symbol`的判断，因为`OrderBook`不会接受不同`symbol`的订单。
        - 删除了对`order`合法性的判断，这个需要在构建`order`的时候进行规避。
        - 不再用`history`列表来记录历史订单，而是用`Log`的方式来记录所有对订单的操作。（这是`OrderBook`最耗时的功能，在原本的实现中，会占用约30%的计算时间。
        - `prettyPrint`方法被弃用，换成输出`LOB`，或者`OCLH`格式的数据。
        - 因为我们可以跟踪到每个订单本身，因此通过在订单中添加操作的方式就能实现对订单的操作和还原，所以我们可以不再使用`Order`的`__deepcopy__`方法。

    6. 重新实现了`OrderBook`的`bids`和`asks`属性：
        原本的实现是二维数组，这种订单虽然在输出为LOB数据的时候具有一定的优势，但是在匹配交易的过程中却需要消耗大量计算。
        考虑到订单匹配时，只从对手盘的最优出价的一个订单开始逐步匹配，因此匹配过程中只需要知道对手盘中最优的限价单即可，为实现最优匹配，我们用`heapq`将其实现为一个优先队列，并在`LimitOrder`类中实现了全序关系的判断。这样就可以在插入时自动按照价格和时间的顺序排列订单。

    6. 重新实现了`handleLimitOrder`方法
        - 按照PEP8规范，将方法改为`handle_limit_order`。
        - 修改了方法的逻辑，原方法先找对手盘，再判断是否具有成交条件。然而并非所有的订单都需要先处理对手盘，而是应该先对比是否比同方向最优出价更优。如果出价非本方向最优，可以直接将订单插入到`OrderBook.ask|bid`订单簿中。
        
        因此订单会自动按照先价格后时间的顺序排列（如果这两个都相同则按照id的顺序从小到大排列）。如果出价高于本方向的最优出价，再处理对手盘。此时会有以下三种情况：
            - 对手盘没有可以匹配的订单，此时直接将订单插入到`OrderBook.ask|bid`订单簿中。
            - 订单被对方全部吃掉，此时在订单的操作记录中设置为已成功交易并处理相关后续操作，处理对手盘订单。（可能有一个或多个订单被吃掉的情况）
            - 订单被部分吃掉，此时在订单的操作记录中设置为已部分交易并处理相关后续操作，处理对手盘订单。（对手盘可能有一个或多个订单被吃掉的情况）

    7. 重新实现了`handelMarketOrder`方法：
        该方法用于处理市价单，但是在原实现中，先将详细的订单簿压缩成只记录价格-量对的列表，然后逐级匹配，直至消耗完所有待匹配市价单，或者吃掉所有对手盘。然后记录下每个价格级别的成交量和价格，然后将这些分别转换成对应大小的`LimitOrder`并调用`handle_limit_order`方法进行处理。这样做的好处是只需要实现一个限价单的处理方法，但是增加了额外的计算开销，并且会产生大量虚拟订单，使得订单记录变得复杂且难以回溯。此外，方法没有考虑到市价单将所有对手盘全部吃掉的情况，也没有区分市价单的类型（我们的重实现中也暂时不考虑市价单的类型）。
        因此我们重新实现了该方法：不再依赖`handle_limit_order`方法，而是直接处理市价单；不再压缩订单簿，而是直接在`OrderBook`中对匹配的订单进行处理。
        - 按照PEP8规范，将方法改为`handle_market_order`。
        - 与`execute_order`方法类似，取消了对`symbol`的判断，删除了对`order`合法性的判断。

        - 删除了`getInsideAsks`和`getInsideBids`方法：该方法用于将对应的订单簿中每个价格档位的订单进行统计（不再区分逐笔订单）。

    8. 删除了`executeOrder`方法：
        该方法用于处理已匹配的两个订单，但是在目前的实现中，已经不再需要单独处理，因为我们在`handle_limit_order`和`handle_market_order`方法中已经处理了所有的订单。也删除了与之相关的`enterBook`方法和`isMatching  `方法。

    9. 删除了`history`列表和`_transacted_volume`字典。
    10. 重新实现了`cancelOrder`方法：
        1. 重命名为`cancel_order`方法
        2. 删除了冗长的实现，因为现在`Order`是可追溯的，且`OrderBook`可以直接通过`Order`的id来获取对应的订单，因此不需要再遍历所有的订单来查找对应的订单，并直接使用数据结构提供的方法来删除指定元素（`get_by_id`方法）
        
    11. 我们重新实现了`modifyOrder`方法，现在不再是使用一个新的`Order`对象来替代原有订单，而是通过一些`modify`方法来调整订单的属性，这些调整也会被记录在`Order`实例中。仅有`LimitOrder`支持修改。

    12. 删除不再需要的`getInsideBids`和`getInsideAsks`方法
    13. 删除不再需要的`_get_recent_history`,`_update_unrolled_transactions`, `_unrolled_transactions_from_order_history`,`get_transacted_volume`, `isBetterPrice`, `isEqualPrice`, `isSameOrder`方法。

    14. 重写`book_log_to_df`方法: TODO

    



    


            


            
            


    

