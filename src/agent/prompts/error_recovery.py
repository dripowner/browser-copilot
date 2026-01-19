"""Стратегии восстановления после ошибок."""

ERROR_RECOVERY_GUIDE = """## Стратегии восстановления после ошибок

### Частые ошибки

**TimeoutError on CDP connection:**
- Сообщи: "Не могу подключиться к браузеру. Проверьте Edge с --remote-debugging-port=9222"
- НЕ вызывай browser_install
- Останови выполнение

**Ref not found:**
- Страница изменилась, refs устарели
- Решение: browser_snapshot() → найди элемент → повтори с новым ref

**Network timeout:**
- Подожди 2-3 секунды, browser_snapshot(), проверь загрузку

**Element not interactive:**
- Проверь альтернативный подход

**Authentication required:**
- Сообщи пользователю, без учетных данных продолжить нельзя

**Dynamic content not appearing:**
- browser_snapshot() снова через 2-3 секунды

### Playwright API Errors

**TimeoutError: locator timeout:**
- Проверь селектор - попробуй более общий
- Увеличь timeout: `click({ timeout: 60000 })`
- Используй getByRole вместо CSS селектора
- Проверь загрузку: `waitForLoadState('networkidle')`

**page.context is not a function:**
- Используй `page.context()` с круглыми скобками

**Element not visible / outside viewport:**
- `await element.scrollIntoViewIfNeeded()`
- Проверь overlay/модалки
- `click({ force: true })` только если уверен
- Альтернативный элемент

**Cannot read property 'textContent' of null:**
- Проверь: `if (await locator.count() === 0) throw Error(...)`
- Безопасный доступ: `(await locator.textContent()) || 'default'`
- Более общий селектор

**Execution context destroyed:**
- Используй `waitForNavigation()` при переходах
- Повтори на новой странице
- Проверь актуальную страницу: `page.context().pages()`

### SPA Errors

**TimeoutError: goto with networkidle:**
- НЕ создавай новую вкладку! Reuse существующую
- Переключись на `waitUntil: 'domcontentloaded'`
- Уменьши timeout до 15 сек
- Жди КОНКРЕТНЫЕ элементы

**TimeoutError: click outside viewport:**
1. `scrollIntoViewIfNeeded()` перед кликом
2. `click({ force: true })` если снова viewport error
3. После 2 viewport errors → `page.evaluate(() => document.querySelector('btn').click())`

**TimeoutError: waitForFunction():**
- Попробуй множественные селекторы: `.product, article, [class*="item"]`
- Увеличь timeout до 15 сек
- Fallback: `waitForTimeout(2000)` вместо waitForFunction
- Verify URL изменился

**InvalidSelectorError:**
- НЕ retry! Исправь синтаксис
- `page.getByRole('button')` - ТОЛЬКО одна роль
- `page.locator('button, a')` - для множественных типов

**TypeError: Promise.slice:**
- Исправь скобки: `(await page.getByRole('button').allTextContents()).slice(0, 10)`
- НЕ retry!

**Stale element reference:**
- Получи НОВЫЙ ref через snapshot/locator
- НЕ retry старую операцию

**Tab proliferation (5+ вкладок):**
- CLEANUP: Закрой дубликаты, оставь первую с target domain
- ВСЕГДА reuse существующей вкладки для retry

### "Click without effect"

**Симптомы:**
- Click success НО URL не изменился
- Click success НО count = 0
- Click success НО корзина пустая

**Root Causes:**
1. Модалка/Overlay блокирует клик → Закрой модалку ПЕРЕД кликом
2. SPA не готов → `waitForLoadState('domcontentloaded')` + пауза
3. `force: true` обход → Убери force, дай Playwright проверить
4. Не тот элемент → Уточни локатор `.not('[hidden]')`

**Recovery (по порядку):**

**Стратегия 1: Закрыть модалки и retry**
```javascript
await page.keyboard.press('Escape');
await page.waitForTimeout(1000);
await page.locator('button').click();
```

**Стратегия 2: Дождаться SPA инициализации**
```javascript
await page.waitForLoadState('domcontentloaded');
await page.waitForTimeout(2000);
await page.locator('button').click();
```

**Стратегия 3: Прямая навигация через URL**
```javascript
const categoryUrl = await page.evaluate(() => btn?.dataset?.url);
if (categoryUrl) await page.goto(categoryUrl, { waitUntil: 'domcontentloaded' });
```

**Стратегия 4: Поиск вместо категорий**
```javascript
const searchBox = page.locator('input[type="search"]');
await searchBox.first().fill('query');
await searchBox.first().press('Enter');
```

**Критерий успеха:** URL изменился ИЛИ count изменился И count > 0

### Общий паттерн

1. Проанализируй ошибку
2. Определи категорию:
   - Syntax Error → ИСПРАВЬ код, НЕ retry
   - Timing Error → ИЗМЕНИ стратегию (domcontentloaded)
   - Tab Management → CLEANUP + reuse
   - Content Error → Альтернативный селектор
3. Примени правильную стратегию
4. НЕ создавай новую вкладку для retry
5. Сообщи пользователю если не можешь восстановиться

### Когда сдаться

После 3 неудачных попыток:
- Сообщи пользователю о проблеме
- Предложи ручное вмешательство
- Спроси стоит ли пробовать другой подход
"""
