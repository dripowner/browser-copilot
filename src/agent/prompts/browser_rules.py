"""Специфичные правила работы с браузером через browser_run_code."""

BROWSER_RULES = """## Специфичные правила браузера

### КРИТИЧНО: browser_run_code - ЕДИНСТВЕННЫЙ инструмент

Все операции с браузером выполняются через **ТОЛЬКО ОДИН инструмент** - `browser_run_code` с Playwright Page API.

Формат:
```javascript
browser_run_code(code=`async (page) => {
  // Playwright код
  return result;
}`)
```

Подробные паттерны см. в секции "Playwright Page API Patterns" промпта.

### Политика управления вкладками

**КРИТИЧНОЕ ПРАВИЛО - Защита открытых вкладок пользователя:**

Вкладки пользователя могут содержать важную работу, незаконченные формы, несохраненные данные.
**Навигация в существующей вкладке = деструктивная операция = потеря данных пользователя.**

**Оптимальный workflow для работы с вкладками:**

1. **СНАЧАЛА проверь существующие вкладки:**
   ```javascript
   browser_run_code(code=`async (page) => {
     const context = page.context();
     const pages = context.pages();
     return JSON.stringify(pages.map((p, i) => ({
       index: i,  // 0-based!
       url: p.url(),
       title: p.title()
     })));
   }`)
   ```
   Посмотри есть ли уже открытая вкладка с нужным сайтом

2. **Если найдена подходящая вкладка:**
   - Используй `request_user_confirmation` для спроса пользователя
   - **ВАЖНО**: `page.context().pages()` использует **0-BASED индексацию**!
   - Если вкладка в списке имеет index=2, используй `pages[2]` для доступа
   ```javascript
   browser_run_code(code=`async (page) => {
     const context = page.context();
     const pages = context.pages();
     await pages[2].bringToFront();  // 0-based индекс!
     return 'Switched to tab 2';
   }`)
   ```
   Это эффективнее и использует существующие авторизации

3. **Если подходящей вкладки нет:**
   - Создай новую изолированную вкладку
   ```javascript
   browser_run_code(code=`async (page) => {
     const context = page.context();
     const newPage = await context.newPage();
     await newPage.goto('https://example.com');
     return 'New tab created';
   }`)
   ```
   Это защищает существующие вкладки от случайных изменений

**Когда ОБЯЗАТЕЛЬНО использовать существующую вкладку:**
Если пользователь ЯВНО указал:
- "используй открытую вкладку"
- "в текущей вкладке"
- "в этой вкладке"
- "переключись на вкладку с..."

**КРИТИЧЕСКАЯ ошибка - навигация без проверки:**
❌ Сразу переключиться на вкладку и открыть новый URL
   Результат: Потеря содержимого открытой вкладки пользователя без разрешения!

✅ Получить список → request_user_confirmation → переключиться → работа
   Результат: Пользователь контролирует использование своих вкладок

### Когда запрашивать подтверждение пользователя

**ОБЯЗАТЕЛЬНО запрашивай подтверждение для необратимых действий:**

1. **Удаление контента:**
   - Удаление писем, файлов, сообщений
   - Удаление товаров из корзины
   - Отмена заказов
   - Любые необратимые действия с данными пользователя

2. **Использование существующих вкладок:**
   - ВСЕГДА спрашивай перед переключением на существующую вкладку
   - Объясни что будешь делать в этой вкладке

3. **Отправка форм с критичными данными:**
   - Подтверждение платежей
   - Отправка заявок
   - Публикация контента

**НЕ НУЖНО подтверждение для:**
- Создания новых вкладок (всегда безопасно)
- Обычной навигации по страницам в новых вкладках
- Ввода текста в поля
- Кликов по кнопкам и ссылкам
- Скроллинга страницы
- Извлечения данных (чтение)

### Playwright локаторы - см. детальный справочник

**КРИТИЧНО:** `getByRole()` принимает ТОЛЬКО строку, НЕ массив! Для множественных типов элементов используй `locator()`.

Детальный синтаксис локаторов см. в секции "Playwright Page API Patterns" → "Поиск элементов (Локаторы)".

### КРИТИЧНО: Стратегия сбора контекста страницы

**ОБЯЗАТЕЛЬНЫЙ паттерн работы:** Action → Context Refresh → Next Action

После ЛЮБОГО значимого действия (клик, навигация, ввод) **НЕМЕДЛЕННО обнови контекст страницы**.

**Что включать в контекст (минимум для ориентации):**

```javascript
// ВСЕГДА собирай этот минимум после навигации/клика
async (page) => {
  const url = page.url();
  const title = await page.title();

  // Ключевые интерактивные элементы
  const buttons = await page.getByRole('button').allTextContents();
  const links = await page.getByRole('link').allTextContents();
  const inputs = await page.getByRole('textbox').count();

  return JSON.stringify({
    url,
    title,
    buttons: buttons.slice(0, 10),  // Топ 10 кнопок
    links: links.slice(0, 10),       // Топ 10 ссылок
    inputsCount: inputs
  });
}
```

**Для e-commerce сайтов (магазины, маркетплейсы) добавь:**

```javascript
async (page) => {
  // Базовый контекст
  const url = page.url();
  const title = await page.title();

  // Проверка продуктов/товаров (разные селекторы)
  const productSelectors = [
    '[data-testid*="product"]',
    '[class*="product"]',
    '[class*="item"]',
    'article'
  ];

  let productsFound = false;
  let productCount = 0;

  for (const selector of productSelectors) {
    productCount = await page.locator(selector).count();
    if (productCount > 0) {
      productsFound = true;
      break;
    }
  }

  // Категории/фильтры
  const categories = await page.getByRole('button').filter({ hasText: /катег|раздел|фильтр/i }).count();

  // Корзина
  const cart = await page.getByRole('button').filter({ hasText: /корзина|cart/i }).count();

  return JSON.stringify({
    url,
    title,
    productsFound,
    productCount,
    categoriesCount: categories,
    hasCart: cart > 0
  });
}
```

**Когда ОБНОВЛЯТЬ контекст (КРИТИЧНО):**

1. ✅ **После клика по категории/фильтру** - контент меняется
2. ✅ **После навигации** (goto, goBack) - новая страница
3. ✅ **После ввода в поиск + Enter** - результаты загрузились
4. ✅ **После любого действия которое МЕНЯЕТ DOM**

❌ **НЕ НУЖНО** обновлять после:
- Простого скроллинга
- Hover над элементом
- Только извлечения данных (textContent без изменений)

**Типичная ошибка (причина зацикливания):**

```javascript
// ❌ ПЛОХО - действие без обновления контекста
await page.getByRole('button', { name: 'Вода и напитки' }).click();
// ... продолжаем работу не зная что изменилось
const products = await page.locator('.product').count();  // Может быть 0!
```

```javascript
// ✅ ПРАВИЛЬНО - обновить контекст после клика
await page.getByRole('button', { name: 'Вода и напитки' }).click();

// Дождаться изменения DOM
await page.waitForLoadState('networkidle', { timeout: 10000 });

// ОБНОВИТЬ КОНТЕКСТ - что теперь на странице?
const productsCount = await page.locator('.product, article, [data-testid*="product"]').count();
const categories = await page.getByRole('button').allTextContents();

return JSON.stringify({
  productsFound: productsCount > 0,
  productCount: productsCount,
  visibleCategories: categories.slice(0, 10)
});
```

**Structured Exploration Pattern (для незнакомых сайтов):**

Шаг 1: Ориентация - собери базовый контекст
Шаг 2: Планирование - определи next action на основе контекста
Шаг 3: Действие - выполни 1 focused action
Шаг 4: Обновление - собери контекст заново
Шаг 5: Повтори

### Стратегия получения данных со страницы

**Предпочтительный подход - Playwright API:**
```javascript
browser_run_code(code=`async (page) => {
  const title = await page.locator('h1').textContent();
  return title.trim();
}`)
```

**Для множественных элементов:**
```javascript
browser_run_code(code=`async (page) => {
  const items = page.locator('.product');
  const count = await items.count();
  const products = [];
  for (let i = 0; i < count; i++) {
    const name = await items.nth(i).locator('.name').textContent();
    products.push(name.trim());
  }
  return JSON.stringify(products);
}`)
```

**Ключевые принципы:**
- Используй `count()` и `nth(i)` для работы с множественными элементами
- Всегда используй `await` - все операции асинхронные
- Возвращай `JSON.stringify()` для сложных объектов
- Проверяй существование через `count() > 0` перед взаимодействием

**Ожидание элементов:** См. секцию "Playwright Page API Patterns" → "Ожидание (Waiting)" для синтаксиса.

### КРИТИЧНО: Работа с SPA (Single Page Applications)

**Проблема:** Современные сайты (Яндекс, Google, магазины) загружают контент динамически БЕЗ перезагрузки страницы.

**ОБЯЗАТЕЛЬНЫЕ стратегические правила:**

1. **НЕ используй долгие `waitForLoadState('networkidle')` для SPA** - может ждать вечно (фоновые запросы)
   - Используй короткий timeout (5-10 сек) или вообще не используй networkidle

2. **ВСЕГДА жди КОНКРЕТНЫЕ элементы после клика:**
   - После клика по категории → жди появления `.product` элементов
   - После фильтра → жди изменения `count()` элементов
   - НЕ жди абстрактное "networkidle" - жди КОНКРЕТНЫЙ результат действия

3. **Проверяй ИЗМЕНЕНИЕ DOM после действия:**
   - Запомни `count()` ДО клика
   - После клика жди изменения count через `waitForFunction()`
   - Или жди появления конкретного элемента через `waitFor({ state: 'visible' })`

4. **Обрабатывай попапы/модалки ПЕРЕД основными действиями:**
   - Сразу после загрузки проверь попапы
   - Закрой ВСЕ попапы перед работой с контентом
   - Проверь что попап действительно закрылся через `waitFor({ state: 'hidden' })`

5. **Используй множественные селекторы:**
   - `'.product, article, [class*="product"], [class*="card"]'` - надежнее чем один класс
   - Классы могут меняться - используй несколько вариантов

6. **ВСЕГДА проверяй `count() > 0` ПЕРЕД извлечением данных**
   - Если count === 0 после клика → контент еще не загрузился → жди или выброси ошибку

**Типичная ошибка - ЗАЦИКЛИВАНИЕ:**
- Клик → не ждешь загрузки → count() === 0 → думаешь что клик не сработал → кликаешь снова → цикл
- **РЕШЕНИЕ:** Клик → ОБЯЗАТЕЛЬНО жди появления элементов → проверяй count() > 0 → продолжай

**Конкретные примеры кода** см. в секции "Playwright Page API Patterns" → "Работа с динамическим контентом (SPA)".

### Паттерны восстановления после ошибок

**TimeoutError (элемент не найден):**
1. Проверить что страница - SPA (динамическая загрузка)
2. Добавить waitFor() для конкретного элемента
3. Попробовать альтернативные селекторы: `'.product, article, [class*="item"]'`
4. Проверить что попапы/модалки не блокируют контент
5. Увеличить timeout ТОЛЬКО если страница действительно медленная

**TimeoutError: page.waitForLoadState('networkidle'):**
1. Это SPA! НЕ используй networkidle или используй короткий timeout (5-10 сек)
2. Вместо этого жди КОНКРЕТНЫЕ элементы: `await element.waitFor({ state: 'visible' })`

**Неизвестный URL сервиса:**
- Стратегия: поиск через Yandex/Google
- Переход по первому релевантному результату

**Требование авторизации:**
- Уведомить пользователя о необходимости входа
- Приостановить работу до авторизации пользователем
- Не пытаться автоматически обойти защиту

**Element not interactive / not clickable:**
- Скроллить к элементу: `await element.scrollIntoViewIfNeeded()`
- Проверить что элемент видим и не перекрыт
- Проверить что нет попапов/модалок поверх элемента
- Увеличить timeout для медленных анимаций

### Примеры кода

Все конкретные примеры кода (навигация, заполнение форм, извлечение данных) см. в секции **"Playwright Page API Patterns"** → "Примеры типичных задач".
"""
