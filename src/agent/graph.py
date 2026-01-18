"""LangGraph Browser Agent with Command API and modular nodes."""

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph

from src.agent.nodes.agent_node import create_agent_node
from src.agent.nodes.reflection.progress_analyzer import create_progress_analyzer
from src.agent.nodes.reflection.quality_evaluator import create_quality_evaluator
from src.agent.nodes.reflection.self_corrector import create_self_corrector
from src.agent.nodes.reflection.strategy_adapter import create_strategy_adapter
from src.agent.nodes.special.human_in_loop import create_human_in_loop
from src.agent.nodes.special.memory_manager import create_memory_manager
from src.agent.nodes.special.progress_reporter import create_progress_reporter
from src.agent.nodes.tools_node import create_tools_node
from src.agent.nodes.validation.critical_action_validator import (
    create_critical_action_validator,
)
from src.agent.nodes.validation.goal_validator import create_goal_validator
from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_browser_agent(llm: ChatOpenAI, tools: list):
    """
    Create browser automation agent with Command API.

    Architecture:
    - Uses Command returns instead of conditional edges
    - Each node decides its own next destination
    - Nodes are independently testable functions
    - Smart routing avoids overhead for simple tasks

    Flow examples:

    Simple task:
        START → agent → tools → agent → goal_validator → END

    Complex task with validation:
        START → agent → critical_action_validator → human_in_loop →
        tools → progress_analyzer → agent → quality_evaluator →
        goal_validator → END

    Args:
        llm: ChatOpenAI instance
        tools: List of LangChain tools from MCP

    Returns:
        Compiled LangGraph agent with checkpointer
    """
    logger.info("Creating modular browser agent with Command API")

    # Create node factories (capture llm and tools in closures)
    agent_node = create_agent_node(llm, tools)
    tools_node = create_tools_node(tools)
    critical_action_validator = create_critical_action_validator(llm)
    goal_validator = create_goal_validator(llm)
    progress_analyzer = create_progress_analyzer(llm)
    strategy_adapter = create_strategy_adapter(llm)
    quality_evaluator = create_quality_evaluator(llm)
    self_corrector = create_self_corrector()
    human_in_loop = create_human_in_loop()
    progress_reporter = create_progress_reporter()
    memory_manager = create_memory_manager(llm)

    # Initialize state graph
    workflow = StateGraph(BrowserAgentState)

    # Add all nodes (NO EDGES - nodes use Command to route!)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("critical_action_validator", critical_action_validator)
    workflow.add_node("goal_validator", goal_validator)
    workflow.add_node("progress_analyzer", progress_analyzer)
    workflow.add_node("strategy_adapter", strategy_adapter)
    workflow.add_node("quality_evaluator", quality_evaluator)
    workflow.add_node("self_corrector", self_corrector)
    workflow.add_node("human_in_loop", human_in_loop)
    workflow.add_node("progress_reporter", progress_reporter)
    workflow.add_node("memory_manager", memory_manager)

    # Only define entry point - rest is Command-based
    workflow.add_edge(START, "agent")

    # Compile with checkpointer for human-in-the-loop support
    memory = MemorySaver()
    agent = workflow.compile(checkpointer=memory)

    logger.info(f"Agent created with {len(tools)} tools and 11 nodes")
    logger.info("Flow control: Command API (nodes decide routing)")

    return agent
