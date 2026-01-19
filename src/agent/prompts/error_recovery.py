"""Стратегии восстановления после ошибок (high-level tools)."""

ERROR_RECOVERY_GUIDE = """## Восстановление после ошибок

### Таблица: Ошибка → Recovery Tools

| Ошибка | Инструменты для восстановления |
|--------|-------------------------------|
| viewport_error | browser_close_modal() → browser_scroll(target) |
| stale_ref | browser_explore_page() → использовать новые selectors |
| timeout | browser_wait_for_load(state="domcontentloaded") → browser_reload() |
| element_not_found | browser_scroll(direction="down") → browser_explore_page() |
| click_no_effect | browser_close_modal() → browser_get_page_info() → browser_explore_page() |

### Частые ситуации

**CDP connection lost:**
- Сообщи: "Потеряно подключение к браузеру. Требуется перезапуск."
- НЕ пытайся исправить автоматически

**Authentication required:**
- Сообщи пользователю через request_user_confirmation()
- Объясни что именно нужно сделать (войти, ввести код)
- Дождись ответа "y" и продолжи

**Modal/Overlay blocks interaction:**
- browser_close_modal(strategy="auto") закроет большинство модалок
- Если не помогло — browser_close_modal(strategy="escape")

**Page not loading:**
1. browser_reload() — перезагрузить страницу
2. browser_wait_for_load(state="domcontentloaded") — дождаться DOM
3. browser_explore_page() — проверить что загрузилось

**Click happened but nothing changed:**
1. browser_get_page_info() — проверить URL (может уже перешли)
2. browser_close_modal() — закрыть возможную модалку
3. browser_explore_page() — найти правильный элемент

### Общий паттерн восстановления

1. Система автоматически определит тип ошибки
2. Ты получишь инструкции с конкретными tools для recovery
3. Выполни предложенные tools
4. Повтори исходное действие
5. Если не помогает — попробуй альтернативный подход
"""
