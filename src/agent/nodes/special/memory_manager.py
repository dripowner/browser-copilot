"""Memory management node using LangMem SummarizationNode."""

from langchain_core.messages.utils import count_tokens_approximately
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langmem.short_term import SummarizationNode

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_memory_manager(llm: ChatOpenAI):
    """
    Factory for memory manager using LangMem SummarizationNode.

    Uses token-based approach instead of fixed message count.
    Integrates with LangMem's progressive summarization system.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Memory management node function
    """

    # Create model for summarization with token limit
    summarization_model = llm.bind(max_tokens=256)

    # Initialize SummarizationNode from LangMem
    summarization_node_impl = SummarizationNode(
        token_counter=count_tokens_approximately,
        model=summarization_model,
        max_tokens=20000,  # Maximum history size
        max_tokens_before_summary=16000,  # Start summarizing when exceeds
        max_summary_tokens=1200,  # Maximum size of summary
        # Output to standard messages field
        output_messages_key="messages",
    )

    def memory_manager(state: BrowserAgentState) -> Command:
        """
        Summarize message history when too long using LangMem.

        Uses token-based approach instead of fixed message count.
        Maintains progressive summary state in context.

        Returns Command routing to "agent" with compressed state.
        """
        logger.info("Checking if message history needs summarization")

        messages = state.get("messages", [])

        # Count tokens in current history
        token_count = count_tokens_approximately(messages)
        logger.info(
            f"Current message history: {len(messages)} messages, ~{token_count} tokens"
        )

        # Call SummarizationNode via invoke method
        # It will automatically decide if summarization is needed based on tokens
        result = summarization_node_impl.invoke(state)

        new_messages = result.get("messages", messages)
        new_context = result.get("context", state.get("context", {}))

        # Check if summarization was performed
        if len(new_messages) < len(messages):
            logger.info(
                f"Summarization performed: {len(messages)} -> {len(new_messages)} messages"
            )
        else:
            logger.info("No summarization needed - history within limits")

        return Command(
            update={
                "messages": new_messages,
                "context": new_context,
            },
            goto="agent",
        )

    return memory_manager
