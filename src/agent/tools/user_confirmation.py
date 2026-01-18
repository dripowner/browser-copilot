"""Tool for requesting user confirmation via Human-in-the-Loop."""

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def request_user_confirmation(
    question: str,
    option_y: str,
    option_n: str,
) -> str:
    """
    Request confirmation or choice from the user. Pauses execution until user responds.

    WHEN TO USE THIS TOOL:

    1. Tab selection - when you find an existing tab that might be suitable:
       - Found a tab with Gmail open and task is about email
       - Found a tab with the target website already loaded
       Example:
         question="Found tab #2 with Gmail already open."
         option_y="use existing tab"
         option_n="open new tab"

    2. Destructive actions - ALWAYS confirm before:
       - Closing browser tabs
       - Deleting items (emails, files, messages, etc.)
       - Submitting forms that can't be undone
       - Removing items from cart
       - Canceling orders
       Example:
         question="Delete this email?"
         option_y="delete"
         option_n="keep"

    3. Ambiguous choices - when multiple valid options exist:
       - Multiple search results match the criteria
       - User intent is unclear from the task

    DO NOT USE for:
    - Regular navigation (just do it)
    - Non-destructive actions (clicking, typing, scrolling)
    - Actions that can be easily undone

    Args:
        question: The question to ask the user (clear and concise)
        option_y: What "y" (yes) means in this context
        option_n: What "n" (no) means in this context

    Returns:
        Human-readable string: "User chose: {selected_option}"

    Note:
        This will pause execution until the user responds with "y" or "n".
    """
    formatted_message = f"{question} (y={option_y}, n={option_n})"

    # Official LangGraph pattern - interrupt directly in tool
    user_response = interrupt({
        "type": "confirmation",
        "message": formatted_message,
        "options": ["y", "n"],
    })

    if user_response == "y":
        return f"User chose: {option_y}"
    else:
        return f"User chose: {option_n}"
