from core.agent.base import BaseAgent
from core.agent.zero_intelligence import ZeroIntelligenceAgent
from core.agent.oracle import OracleAgent
from core.agent.background import BackgroundAgent
from core.agent.noise import NoiseAgent
from core.agent.value import ValueAgent
from core.agent.obi import OrderBookImbalanceAgent
from core.agent.hbl import HeuristicBeliefLearningAgent
from core.agent.fundamental import FundamentalTrackingAgent
from core.agent.replay import HistoricalOrderReplayAgent

# from agent.trading_agent import TradingAgent
# from agent.noise_agent import NoiseAgent
# from agent.value_agent import ValueAgent
# from agent.market_makers.AdaptiveMarketMakerAgent import AdaptiveMarketMakerAgent
# from agent.examples.MomentumAgent import MomentumAgent
# from agent.execution.POVExecutionAgent import POVExecutionAgent


AGENTS = {
    "base": BaseAgent,
    "zero_intelligence": ZeroIntelligenceAgent,
    "oracle": OracleAgent,
    "background": BackgroundAgent,
    "noise": NoiseAgent,
    "value": ValueAgent,
    "order_book_imbalance": OrderBookImbalanceAgent,
    "hbl": HeuristicBeliefLearningAgent,
    "fundamental_tracking": FundamentalTrackingAgent,
    "historical_order_replay": HistoricalOrderReplayAgent,
    # "market_maker": AdaptiveMarketMakerAgent,
    # "momentum": MomentumAgent,
    # "pov_execution": POVExecutionAgent,
}

__all__ = [
    "AGENTS",
    "BaseAgent",
    "ZeroIntelligenceAgent",
    "OracleAgent",
    "BackgroundAgent",
    "NoiseAgent",
    "ValueAgent",
    "OrderBookImbalanceAgent",
    "HeuristicBeliefLearningAgent",
    "FundamentalTrackingAgent",
    "HistoricalOrderReplayAgent",
    # "AdaptiveMarketMakerAgent",
    # "MomentumAgent",
    # "POVExecutionAgent",
]
