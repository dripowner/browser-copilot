"""CLI interface для Browser Copilot Agent."""

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.utils.logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def _create_initial_state(query: str) -> dict:
    """
    Create initial state for a new task.

    Args:
        query: User's task query

    Returns:
        Initial BrowserAgentState dict
    """
    return {
        "messages": [HumanMessage(content=query)],
        "original_task": query,
        "needs_validation": False,
        "validation_passed": False,
        "requires_human_approval": False,
        "pending_action": None,
        "progress_score": 0.0,
        "message_count_at_last_check": 0,
        "strategy_changes": 0,
        "error_count": 0,
        "stuck_counter": 0,
        "context": {},  # For LangMem SummarizationNode
        "loop_count": 0,
        "last_node": "START",
        "retry_count": 0,
        "goal_achieved": False,
        "last_error": None,
        "error_type": None,
        "quality_score": None,
    }


async def run_cli(agent: Any) -> None:
    """
    Запустить интерактивный CLI для взаимодействия с агентом.

    Args:
        agent: Compiled LangGraph agent

    Example:
        >>> agent = create_browser_agent(llm, tools)
        >>> await run_cli(agent)
    """
    console.print(
        Panel.fit(
            "[bold cyan]Browser Copilot Agent[/bold cyan]\n"
            "Автономный AI-агент для управления браузером\n\n"
            "Команды:\n"
            "  [yellow]exit/quit[/yellow] - Выход\n"
            "  [yellow]help[/yellow] - Помощь",
            title="Добро пожаловать!",
        )
    )

    while True:
        try:
            # Получаем задачу от пользователя
            query = Prompt.ask("\n[bold green]Задача[/bold green]")

            if not query.strip():
                continue

            if query.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]До свидания![/yellow]")
                break

            if query.lower() == "help":
                show_help()
                continue

            # Выполняем задачу
            console.print("[cyan]Агент работает...[/cyan]")
            logger.info(f"User query: {query}")

            try:
                # Создаем initial state для новой задачи
                initial_state = _create_initial_state(query)

                # Создаем config с thread_id для checkpointer
                config = {"configurable": {"thread_id": f"task-{hash(query)}"}}

                # Используем stream для обработки interrupts
                final_result = None

                async for chunk in agent.astream(
                    initial_state, config, stream_mode="updates"
                ):
                    # Обрабатываем chunk
                    if "__interrupt__" in chunk:
                        # Human-in-the-loop interrupt
                        interrupt_data = chunk["__interrupt__"][0]

                        # Get user response
                        user_response = await _handle_interrupt_async(interrupt_data)

                        # Resume with Command(resume=value) to pass value back to interrupt()
                        logger.info("Resuming agent execution after interrupt")
                        async for resume_chunk in agent.astream(
                            Command(resume=user_response), config, stream_mode="updates"
                        ):
                            # Обработка вложенных interrupts
                            if "__interrupt__" in resume_chunk:
                                logger.warning(
                                    "Nested interrupt detected during resume - not yet supported. "
                                    "Please simplify task to avoid multiple interrupts."
                                )
                                # TODO: Implement recursive interrupt handling
                                # Requires restructuring to handle arbitrary nesting depth
                            else:
                                # Обычная обработка chunks после resume
                                for node_name, node_output in resume_chunk.items():
                                    if node_name == "progress_reporter":
                                        # Отображаем progress report
                                        message_count = len(
                                            node_output.get("messages", [])
                                        )
                                        progress_score = node_output.get(
                                            "progress_score", 0.0
                                        )
                                        error_count = node_output.get("error_count", 0)

                                        # Генерация семантического статуса
                                        if progress_score >= 0.9:
                                            status = "Near completion"
                                        elif progress_score >= 0.6:
                                            status = "Making progress"
                                        elif progress_score >= 0.3:
                                            status = "Working"
                                        else:
                                            status = "Starting"

                                        if message_count > 0:
                                            progress_text = f"[{status}] {int(progress_score * 100)}% - {message_count} exchanges, {error_count} errors"
                                            console.print(f"[dim]{progress_text}[/dim]")

                                final_result = resume_chunk

                        # Resume цикл завершен - продолжаем основной stream цикл
                        # Основной цикл получит все последующие updates до END
                        logger.info("Resume completed, continuing main stream loop")
                    else:
                        # Regular chunk - может содержать progress reports
                        for node_name, node_output in chunk.items():
                            if node_name == "progress_reporter":
                                # Отображаем progress report из state (не из messages)
                                message_count = len(node_output.get("messages", []))
                                progress_score = node_output.get("progress_score", 0.0)
                                error_count = node_output.get("error_count", 0)

                                # Генерация семантического статуса
                                if progress_score >= 0.9:
                                    status = "Near completion"
                                elif progress_score >= 0.6:
                                    status = "Making progress"
                                elif progress_score >= 0.3:
                                    status = "Working"
                                else:
                                    status = "Starting"

                                if message_count > 0:
                                    progress_text = f"[{status}] {int(progress_score * 100)}% - {message_count} exchanges, {error_count} errors"
                                    console.print(f"[dim]{progress_text}[/dim]")

                        final_result = chunk

                # Получаем финальное состояние графа после завершения
                final_state = agent.get_state(config)

                if final_state and final_state.values:
                    messages = final_state.values.get("messages", [])

                    if messages:
                        # Ищем последний AIMessage с содержательным ответом
                        final_message = None
                        for msg in reversed(messages):
                            if hasattr(msg, "content") and msg.content:
                                # Пропускаем технические сообщения
                                content_str = str(msg.content)
                                if not content_str.startswith("Goal validation:"):
                                    final_message = msg
                                    break

                        if final_message:
                            content = final_message.content
                            console.print(
                                Panel(
                                    f"[green]{content}[/green]",
                                    title="Результат",
                                    border_style="green",
                                )
                            )
                        else:
                            console.print(
                                "[yellow]Агент не вернул содержательный ответ[/yellow]"
                            )
                    else:
                        console.print("[yellow]Агент не вернул ответ[/yellow]")
                else:
                    console.print("[yellow]Агент не завершил выполнение[/yellow]")

            except Exception as e:
                logger.error(f"Error during agent execution: {e}", exc_info=True)
                console.print(
                    Panel(
                        f"[red]Ошибка: {str(e)}[/red]",
                        title="Ошибка выполнения",
                        border_style="red",
                    )
                )

        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Прервано пользователем. Используйте 'exit' для выхода.[/yellow]"
            )
            continue
        except EOFError:
            console.print("\n[yellow]До свидания![/yellow]")
            break


async def _handle_interrupt_async(interrupt_obj: Any) -> str:
    """
    Handle human-in-the-loop interrupt (async version).

    Args:
        interrupt_obj: Interrupt object from LangGraph

    Returns:
        User response string
    """
    # Extract value from Interrupt object
    interrupt_data = (
        interrupt_obj.value if hasattr(interrupt_obj, "value") else interrupt_obj
    )

    # Handle dict or direct value
    if isinstance(interrupt_data, dict):
        message = interrupt_data.get("message", "Требуется подтверждение")
        options = interrupt_data.get("options", ["yes", "no"])
    else:
        message = str(interrupt_data)
        options = ["yes", "no"]

    # Запрашиваем ответ пользователя
    user_response = Prompt.ask(
        f"\n[bold yellow]{message}[/bold yellow]", choices=options
    )

    return user_response


def show_help() -> None:
    """Показать справку по использованию."""
    help_text = """
[bold]Примеры задач:[/bold]

[cyan]1. Простая навигация:[/cyan]
   "Открой yandex.ru и найди погоду в Москве"

[cyan]2. Работа с почтой:[/cyan]
   "Прочитай последние 5 писем и удали спам"

[cyan]3. Заказ еды:[/cyan]
   "Найди BBQ-бургер на delivery-club.ru и добавь в корзину"

[cyan]4. Поиск вакансий:[/cyan]
   "Найди 3 вакансии Python разработчика на hh.ru"

[bold]Советы:[/bold]
- Формулируй задачи чётко и конкретно
- Агент автоматически составит план и выполнит его
- При необходимости агент запросит дополнительную информацию

[bold]Новые возможности:[/bold]
- ✅ Валидация критических действий (удаление, отправка форм)
- ✅ Автоматическое исправление ошибок (stale references)
- ✅ Адаптация стратегии при застревании
- ✅ Progress reports для длительных задач

[bold]Требования:[/bold]
- Для задач с авторизацией: войди в аккаунты заранее
  (сессия сохранится благодаря персистентности)
    """

    console.print(Panel(help_text, title="Справка", border_style="blue"))
