"""
Browser Copilot - Автономный AI-агент для управления браузером.

Entry point для запуска агента.
"""

import asyncio
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from rich.console import Console

from src.agent.graph import create_browser_agent
from src.ui.cli import run_cli
from src.utils.config import load_config
from src.utils.logger import setup_logger

console = Console()
logger = setup_logger(__name__)


async def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Загрузка конфигурации
        console.print("[cyan]Загрузка конфигурации...[/cyan]")
        config = load_config()
        logger.info("Configuration loaded successfully")

        # Инициализация LLM
        console.print(f"[cyan]Подключение к LLM: {config.llm_model}...[/cyan]")
        llm = ChatOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
            temperature=config.llm_temperature,
            streaming=False,
        )
        logger.info(f"LLM client created: {config.llm_model}")

        # Инициализация MCP Client
        console.print("[cyan]Запуск MCP сервера через stdio...[/cyan]")

        mcp_client = MultiServerMCPClient(
            {
                "browsermcp": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": [
                        "-y",
                        "@playwright/mcp@latest",
                        "--cdp-endpoint",
                        "http://127.0.0.1:9222",
                        "--snapshot-mode",
                        "none",
                        "--image-responses",
                        "omit",
                    ],
                }
            }
        )

        # Получение tools из MCP сервера
        try:
            all_mcp_tools = await mcp_client.get_tools()

            # Найти browser_run_code для внутреннего использования
            browser_run_code_tool = next(
                (tool for tool in all_mcp_tools if tool.name == "browser_run_code"),
                None,
            )

            if browser_run_code_tool is None:
                console.print(
                    "[red]✗ browser_run_code не найден в MCP сервере[/red]"
                )
                return 1

            logger.info(f"Available MCP tools: {[tool.name for tool in all_mcp_tools]}")
            console.print("[green]✓ Найден browser_run_code в MCP сервере[/green]")

            # Инициализация BrowserExecutor с MCP tool
            from src.agent.tools._executor import BrowserExecutor

            BrowserExecutor.initialize(browser_run_code_tool)
            console.print("[green]✓ BrowserExecutor инициализирован[/green]")

            # Получение высокоуровневых browser tools
            from src.agent.tools import get_browser_tools
            from src.agent.tools.user_confirmation import request_user_confirmation

            browser_tools = get_browser_tools()
            tools = browser_tools + [request_user_confirmation]

            console.print(
                f"[green]✓ Итого инструментов: {len(tools)} "
                f"({len(browser_tools)} browser + 1 HITL)[/green]"
            )
            logger.info(f"All tools: {[tool.name for tool in tools]}")

        except Exception as e:
            logger.error(f"Failed to get tools from MCP: {e}", exc_info=True)
            console.print(f"[red]✗ Не удалось получить tools из MCP сервера: {e}[/red]")
            console.print(
                "\n[yellow]Убедитесь что npx доступен и @browsermcp/mcp установлен:[/yellow]"
            )
            console.print("[yellow]  npm install -g @browsermcp/mcp@latest[/yellow]\n")
            return 1

        # Создание агента
        console.print("[cyan]Создание агента...[/cyan]")
        agent = create_browser_agent(llm, tools)
        console.print("[green]✓ Агент создан[/green]\n")

        # Запуск CLI
        try:
            await run_cli(agent)
        except KeyboardInterrupt:
            console.print("\n[yellow]Прервано пользователем[/yellow]")

        return 0

    except FileNotFoundError as e:
        console.print(f"[red]Ошибка: Файл не найден: {e}[/red]")
        console.print(
            "\n[yellow]Создайте файл .env на основе config/.env.example[/yellow]"
        )
        return 1

    except ValueError as e:
        console.print(f"[red]Ошибка конфигурации: {e}[/red]")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        console.print(f"[red]Неожиданная ошибка: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
