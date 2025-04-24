from agent.base import Agent
from agent.trading_agent import TradingAgent
from agent.noise_agent import NoiseAgent
from agent.value_agent import ValueAgent
from agent.market_makers.AdaptiveMarketMakerAgent import AdaptiveMarketMakerAgent
from agent.examples.MomentumAgent import MomentumAgent
from agent.execution.POVExecutionAgent import POVExecutionAgent


agents = {
    "base": Agent,
    "trading": TradingAgent,
    "noise": NoiseAgent,
    "value": ValueAgent,
    "market_maker": AdaptiveMarketMakerAgent,
    "momentum": MomentumAgent,
    "pov_execution": POVExecutionAgent,
}

__all__ = [
    "agents",
    "Agent",
    "TradingAgent",
    "NoiseAgent",
    "ValueAgent",
    "AdaptiveMarketMakerAgent",
    "MomentumAgent",
    "POVExecutionAgent",
]
