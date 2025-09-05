from core.agent.base import BaseAgent
from core.agent.zero_intelligence import ZeroIntelligenceAgent
from core.agent.oracle import OracleAgent
from core.agent.background import BackgroundAgent

# from agent.trading_agent import TradingAgent
# from agent.noise_agent import NoiseAgent
# from agent.value_agent import ValueAgent
# from agent.market_makers.AdaptiveMarketMakerAgent import AdaptiveMarketMakerAgent
# from agent.examples.MomentumAgent import MomentumAgent
# from agent.execution.POVExecutionAgent import POVExecutionAgent


agents = {
    "base": BaseAgent,
    "zero_intelligence": ZeroIntelligenceAgent,
    "oracle": OracleAgent,
    "background": BackgroundAgent,
    # "trading": TradingAgent,
    # "noise": NoiseAgent,
    # "value": ValueAgent,
    # "market_maker": AdaptiveMarketMakerAgent,
    # "momentum": MomentumAgent,
    # "pov_execution": POVExecutionAgent,
}

__all__ = [
    "agents",
    "BaseAgent",
    "ZeroIntelligenceAgent",
    "OracleAgent",
    "BackgroundAgent",
    # "TradingAgent",
    # "NoiseAgent",
    # "ValueAgent",
    # "AdaptiveMarketMakerAgent",
    # "MomentumAgent",
    # "POVExecutionAgent",
]
