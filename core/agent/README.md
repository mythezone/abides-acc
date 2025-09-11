# Agent类型

目前有12个类型的Agent:
* Background Agent
* Oracle Agent

* Near Zero Intelligence Agent
* BDI Agent
* Chartist Agent
* FCN Agent 
* GP Agent
* Informed Agent
* Uninformed Agent
* Liquidity Provider Agent
* Liquidity Taker Agent

---
待实现的Agent类型：
* High Frequency Agent

* Market 

--- 
ABIDES中原有的Agent：
* Market Makers
    * Adaptive Market Maker Agent
    * Market Maker Agent
    * POV Market Maker Agent
    * Spread Based Market Maker Agent

* Fundamental Tracking Agent 
* Heuristic Belief Learning Agent 
* Order Book Balance Agent 
* Value Agent 
* Trading Agent 
* Zero Intelligence Agent

---
* Example Agent
    * Momentum Agent
    * Impact Agent 
    * Market Replay Agent 
    * QLearning Agent 
    * Shock Agent
    * Subscription Agent 
    * Sum Client Agent 
    * Sum Service Agent 

## 代办
* 添加Agent时，检查一下Agent的作用


### Introduction

* 需求
    * 从现实出发的需求
        * 要达到某个目的需要满足的需求
            * 公开（服务化）可用（前端，可靠）的全尺度（性能）金融仿真器（自校准）

    * 为什么我们需要来实现这个系统？
        * 其他系统无法满足上述需求
        * 需要什么功能？
        * 为什么需要这些功能？

* GAP（Related Work）
    * 现有的系统对这些需求（功能）实现得如何？
    * 和现有的相似的系统相比，有什么新功能，新特性？
        * 用一个表对比现有系统和我们提出的系统之间的功能差别

* 实现
    * 我们怎么实现这些功能？
        * 架构图
        * 流程图
        * UML设计图

* 实验（我们实现的怎么样？）
    * 性能
        * 系统可扩展性
            * 随着订单量增加，仿真效率的变化
            * 随着股票数量增加（相同订单量），仿真效率的变化
            * 随着计算资源增加，极限压力下的仿真效率的变化
            * 与其他系统做对比（公平性）
                * 保持Agent数量/类型一致
        * 自校准性能
            * 对比真是数据-仿真数据差异
                * 选择哪些数据（真实数据）？
                * 配置哪些Agent（类型，数量）？
                * Scaled
            * 对比其他方法的校准效率（公平性）
        * 

* Case Study
    * 功能
        * 多资产（跨市场，待实现）支持
            * 跨股票传播
        * 多时段，跨日机制
        * 自校准支持
        * 前端（Terminal，Web端，体现可交互性）

## 下周预计
* Agent类型实现
* 性能测试的初步数据
    * 实验设置
    * 结果表->图



