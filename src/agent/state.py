"""State definition for Browser Copilot Agent."""

from typing import Annotated, Any, Dict, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class BrowserAgentState(TypedDict):
    """
    Complete state for browser automation agent.

    Extends MessagesState with additional metadata for validation,
    reflection, error handling, and flow control.
    """

    # Core messaging (compatible with MessagesState)
    messages: Annotated[list[BaseMessage], add_messages]

    # Task metadata
    original_task: str  # User's original request

    # Validation flags
    needs_validation: bool  # Does next action need validation?
    validation_passed: bool  # Did validation succeed?
    requires_human_approval: bool  # Should pause for user?
    pending_action: Optional[str]  # Action waiting for approval

    # Reflection data
    progress_score: float  # 0.0 to 1.0, how close to completion
    message_count_at_last_check: int  # Track when we last ran analysis/reporting
    strategy_changes: int  # How many times strategy was adapted
    stuck_counter: int  # Consecutive cycles without progress

    # Memory management (LangMem integration)
    context: Dict[str, Any]  # Required by SummarizationNode for tracking state

    # Flow control
    loop_count: int  # Prevent infinite loops
    last_node: str  # Track previous node for debugging

    # Quality metrics
    quality_score: Optional[float]  # Final quality evaluation
    goal_achieved: bool  # Did we meet the original goal?
