"""Playwright Page API patterns for browser_run_code tool.

This module provides comprehensive guide on using Playwright Page API
through the browser_run_code tool. All browser operations must use this
single tool with Playwright code.
"""

PLAYWRIGHT_PATTERNS = """## Playwright Page API Patterns

**NOTE:** Code examples use common web application patterns (`.product-card`, `.price`, etc.) for demonstration.
These are illustrative examples - adapt selectors, terminology, and patterns to match your specific application's structure.

### КРИТИЧНО: browser_run_code - ЕДИНСТВЕННЫЙ инструмент для браузера

Все операции с браузером выполняются через browser_run_code с Playwright Page API.

**Формат вызова:**
```javascript
browser_run_code(code=`async (page) => {
  // Playwright код здесь
  return result;
}`)
```

Аргумент `page` - это Playwright Page object с полным API для работы с браузером.

---

### Навигация

**Переход на страницу:**
```javascript
async (page) => {
  // Для SPA используй 'domcontentloaded', для статичных сайтов можно 'networkidle'
  await page.goto('https://example.com');
  await page.waitForLoadState('domcontentloaded');  // Быстро для SPA
  return 'Navigated to example.com';
}
```

**Навигация назад/вперед:**
```javascript
async (page) => {
  await page.goBack();
  return 'Navigated back';
}

async (page) => {
  await page.goForward();
  return 'Navigated forward';
}
```

**Перезагрузка страницы:**
```javascript
async (page) => {
  await page.reload();
  return 'Page reloaded';
}
```

---

### Управление вкладками

**🚨 ОБЯЗАТЕЛЬНЫЙ ПАТТЕРН: Tab Selection Workflow (ПЕРЕД ЛЮБОЙ НАВИГАЦИЕЙ)**

Этот паттерн ОБЯЗАТЕЛЕН перед любым `page.goto()` на новый домен:

```javascript
async (page) => {
  const targetDomain = 'lavka.yandex.ru';
  const targetUrl = 'https://lavka.yandex.ru/';

  // Шаг 1: Получить все вкладки
  const context = page.context();
  const pages = context.pages();

  // Шаг 2: Найти подходящую вкладку (УЖЕ на нужном домене)
  const existingTab = pages.find(p => p.url().includes(targetDomain));

  // Шаг 3: Выбрать или создать вкладку
  let workingPage;

  if (existingTab) {
    // Подходящая вкладка найдена - переключиться
    workingPage = existingTab;
    await workingPage.bringToFront();
  } else {
    // Подходящей вкладки НЕТ - создать НОВУЮ
    workingPage = await context.newPage();
  }

  // Шаг 4: Теперь безопасно делать навигацию
  await workingPage.goto(targetUrl, { waitUntil: 'domcontentloaded' });

  return `Navigated to ${targetDomain} in ${existingTab ? 'existing' : 'new'} tab`;
}
```

**ПОЧЕМУ это критично:**
- ❌ БЕЗ проверки: `page.goto()` перезапишет контент ТЕКУЩЕЙ вкладки (может быть важная страница пользователя)
- ✅ С проверкой: навигация только в правильной вкладке (существующей или новой)

---

**Получить список всех открытых вкладок:**
```javascript
async (page) => {
  const context = page.context();
  const pages = context.pages();

  const tabsInfo = await Promise.all(
    pages.map(async (p, i) => ({
      index: i,  // 0-based!
      url: p.url(),
      title: await p.title()
    }))
  );

  return JSON.stringify(tabsInfo);
}
```

**Создать новую вкладку:**
```javascript
async (page) => {
  const context = page.context();
  const newPage = await context.newPage();
  await newPage.goto('https://example.com');
  return `New tab created and navigated to example.com`;
}
```

**Переключиться на другую вкладку:**
```javascript
async (page) => {
  const context = page.context();
  const pages = context.pages();

  // ВАЖНО: pages - это массив с 0-based индексацией!
  const targetPage = pages[2];  // Третья вкладка (индекс 2)
  await targetPage.bringToFront();

  return 'Switched to tab with index 2';
}
```

---

### Поиск элементов (Локаторы)

**КРИТИЧНО: getByRole() принимает ТОЛЬКО ОДНУ роль (строку)!**

❌ **НИКОГДА НЕ ДЕЛАЙ ТАК:**
```javascript
// ОШИБКА: массив не поддерживается!
page.getByRole(['button', 'link'])  // InvalidSelectorError!
page.getByRole([...])               // ВСЕГДА ошибка!
```

✅ **ПРАВИЛЬНО - для одной роли:**
```javascript
page.getByRole('button')      // Только кнопки
page.getByRole('link')        // Только ссылки
page.getByRole('textbox')     // Только текстовые поля
```

✅ **ПРАВИЛЬНО - для НЕСКОЛЬКИХ типов элементов используй locator():**
```javascript
// Найти кнопки И ссылки одновременно
page.locator('button, a, [role="button"], [role="link"]')

// Найти элементы с классами
page.locator('.product, .item, article')

// Комбинация - ТОЛЬКО через locator()
page.locator('[data-testid*="product"], .product, article')
```

**Современные локаторы (РЕКОМЕНДУЕТСЯ - accessibility-first):**
```javascript
async (page) => {
  // По ARIA роли - ТОЛЬКО ОДНА роль!
  const submitBtn = page.getByRole('button', { name: 'Submit' });
  const allButtons = page.getByRole('button');  // Все кнопки

  // По видимому тексту
  const link = page.getByText('Click here');

  // По placeholder
  const emailInput = page.getByPlaceholder('Email address');

  // По label
  const usernameField = page.getByLabel('Username');

  // По alt тексту (для изображений)
  const image = page.getByAltText('Company logo');

  // По title
  const helpIcon = page.getByTitle('Help');

  return 'Locators created';
}
```

**Фильтрация локаторов (hasText, has, filter):**
```javascript
async (page) => {
  // Фильтр по тексту (регулярное выражение)
  const drinkCategory = page.getByRole('button').filter({ hasText: /напит|вода/i });

  // Множественные типы с фильтром - через locator()
  const anyDrinkBtn = page.locator('button, a, [role="button"]').filter({ hasText: /напит/i });

  // Фильтр по вложенному элементу
  const cardWithButton = page.locator('.product-card').filter({
    has: page.getByRole('button', { name: 'Add to cart' })
  });

  return 'Filtered locators created';
}
```

**CSS/XPath селекторы (если необходимо):**
```javascript
async (page) => {
  // CSS селекторы - для МНОЖЕСТВЕННЫХ типов
  const element = page.locator('button.submit');
  const byId = page.locator('#email-input');
  const byClass = page.locator('.error-message');

  // Множественные типы элементов
  const interactive = page.locator('button, a, input');

  // XPath (редко нужно)
  const byXPath = page.locator('xpath=//button[@type="submit"]');

  return 'CSS/XPath locators created';
}
```

---

### Взаимодействие с элементами

#### Selector Strategy: Выбор ПРАВИЛЬНЫХ интерактивных элементов

**КРИТИЧЕСКАЯ ПРОБЛЕМА:** `.first()` и `querySelector()` могут вернуть НЕПРАВИЛЬНЫЙ элемент.

**Почему это происходит:**
- На странице может быть несколько кнопок (добавить, удалить, закрыть)
- `.first()` возвращает ПЕРВУЮ в DOM, не обязательно нужную
- Первая кнопка может быть **disabled**, **hidden** или **aria-hidden**
- Клик на disabled элемент → Playwright timeout (правильное поведение!)

**Типичная ошибка:**
```javascript
❌ НЕ делай так:
const btn = page.locator('button').first();  // Может быть disabled минус!
await btn.click();  // TimeoutError - кнопка disabled
```

---

**ПРАВИЛЬНАЯ СТРАТЕГИЯ: Фильтрация перед выбором**

**1. Фильтр по семантике (текст, роль, атрибуты):**

```javascript
✅ Правильно - по тексту кнопки:
await page.locator('button').filter({ hasText: '+' }).click();
await page.locator('button').filter({ hasText: /Добавить|Add/ }).click();

✅ Правильно - по role и name:
await page.getByRole('button', { name: /Add|Добавить/ }).click();

✅ Правильно - по data-атрибуту:
await page.locator('button[data-action="add"]').click();
```

**2. Фильтр по состоянию (enabled, visible):**

```javascript
✅ Проверка перед click:
const btn = page.locator('button').filter({ hasText: '+' });
const isEnabled = await btn.isEnabled();
const isVisible = await btn.isVisible();

if (isEnabled && isVisible) {
  await btn.click();
} else {
  throw new Error('Button is disabled or hidden - cannot click');
}
```

**3. Фильтр исключением (НЕ disabled, НЕ hidden):**

```javascript
✅ Исключаем disabled элементы:
// CSS-селектор с исключением
await page.locator('button:not([disabled]):not([aria-hidden])').first().click();

// Или через filter
const enabledButtons = await page.locator('button').evaluateAll(buttons => {
  return buttons.filter(b => !b.disabled && b.offsetParent !== null);
});
```

---

**ПОЛНЫЙ WORKFLOW для выбора кнопки:**

**Приоритет стратегий (от лучшего к худшему):**

```javascript
// Шаг 1: Семантический поиск (ЛУЧШИЙ способ)
try {
  await page.getByRole('button', { name: /Add|Добавить|\+/ }).click();
  return 'Success - semantic selector';
} catch (e) {
  // Переход к Шагу 2
}

// Шаг 2: Фильтр по тексту
try {
  await page.locator('button').filter({ hasText: /\+|Add/ }).first().click();
  return 'Success - text filter';
} catch (e) {
  // Переход к Шагу 3
}

// Шаг 3: Фильтр по состоянию
try {
  const buttons = await page.locator('button').all();
  for (const btn of buttons) {
    const isEnabled = await btn.isEnabled();
    const isVisible = await btn.isVisible();
    if (isEnabled && isVisible) {
      await btn.click();
      return 'Success - state filter';
    }
  }
  throw new Error('No enabled buttons found');
} catch (e) {
  // Шаг 4: Ошибка - ни одна кнопка не подходит
  throw new Error('Could not find clickable button - all are disabled or hidden');
}
```

---

**ANTI-PATTERNS (типичные ошибки):**

❌ **Ошибка 1: Слепое использование .first()**
```javascript
// ❌ Может вернуть disabled кнопку "минус"
const btn = card.locator('button').first();
await btn.click();  // TimeoutError!
```

✅ **Правильно:**
```javascript
// ✅ Ищем кнопку с плюсом
const addBtn = card.locator('button').filter({ hasText: '+' });
if (await addBtn.count() > 0) {
  await addBtn.click();
}
```

❌ **Ошибка 2: querySelector без проверки состояния**
```javascript
// ❌ В evaluate() не видно что кнопка disabled
await page.evaluate(() => {
  const btn = document.querySelector('button');  // Может быть disabled!
  btn.click();  // Click без эффекта
});
```

✅ **Правильно:**
```javascript
// ✅ Playwright автоматически проверяет enabled
await page.locator('button').filter({ hasText: '+' }).click();
```

❌ **Ошибка 3: Игнорирование aria-hidden**
```javascript
// ❌ Элемент может быть скрыт для accessibility
const btn = page.locator('[class*="button"]').first();
```

✅ **Правильно:**
```javascript
// ✅ Исключаем aria-hidden
const btn = page.locator('button:not([aria-hidden="true"])').first();
```

---

**KEY INSIGHT:**

**Порядок выбора элемента:**
1. **Семантика** (роль, текст, label) - самый надежный
2. **Состояние** (enabled, visible) - фильтр невалидных
3. **Позиция** (.first(), .last()) - только если уверен

**Никогда не начинай с позиции** - это путь к disabled элементам и timeout ошибкам!

---

#### Counter Buttons Pattern (Add/Remove Controls)

**КРИТИЧЕСКАЯ ПРОБЛЕМА:** Многие сайты используют счетчики товаров с кнопками увеличения/уменьшения:

```
[−] [0] [+]  ← Когда товара нет в корзине
[−] [1] [+]  ← Когда товар добавлен
```

**Проблема:** `.first()` или `buttons[0]` выбирает кнопку **МИНУС** (disabled когда count=0)!

```javascript
❌ НЕ делай так:
const btn = card.locator('button').first();  // Это МИНУС - disabled!
await btn.click();  // TimeoutError - кнопка disabled
```

**Почему это происходит:**
- В DOM структуре счетчика кнопка минус идет **ПЕРВОЙ**: `<button>−</button> <span>0</span> <button>+</button>`
- `.first()` возвращает первую кнопку = минус
- Когда товара нет в корзине (count=0), минус **disabled**
- Playwright timeout при попытке клика на disabled элемент

**ПРАВИЛЬНАЯ СТРАТЕГИЯ - выбор кнопки ПЛЮС:**

**1. По data-атрибуту (ЛУЧШИЙ способ):**
```javascript
✅ Используй data-testid если доступен:
await page.locator('[data-testid="add-spin-button"]').click();
await page.locator('button[data-action="increment"]').click();
```

**2. По aria-label:**
```javascript
✅ Фильтр по семантическому атрибуту:
await page.locator('button[aria-label*="Добавить"]').click();
await page.locator('button[aria-label*="Add"]').click();
await page.locator('button[aria-label*="Increase"]').click();
```

**3. По тексту кнопки:**
```javascript
✅ Фильтр по символу плюс:
await page.locator('button').filter({ hasText: '+' }).click();
await page.locator('button').filter({ hasText: /\+|Add|Добавить/i }).click();
```

**4. Исключить disabled и взять ПОСЛЕДНЮЮ:**
```javascript
✅ Плюс обычно справа (последняя enabled кнопка):
const buttons = card.locator('button:not([disabled])');
const addBtn = buttons.last();  // Последняя = плюс
await addBtn.click();
```

**5. Через nth() (если знаешь позицию):**
```javascript
✅ Третья кнопка в структуре [-] [count] [+]:
const buttons = card.locator('button');
const addBtn = buttons.nth(2);  // 0-based: 0=минус, 1=count?, 2=плюс
await addBtn.click();

// НО лучше проверить структуру сначала
const count = await buttons.count();
if (count >= 3) {
  await buttons.nth(count - 1).click();  // Последняя
}
```

---

**ПОЛНЫЙ WORKFLOW для счетчиков:**

```javascript
async (page) => {
  const card = page.locator('article').filter({ hasText: 'Product Name' });

  // СТРАТЕГИЯ 1: Data-атрибут (если доступен)
  let addBtn = card.locator('button[data-testid*="add"], button[data-action="increment"]');

  // СТРАТЕГИЯ 2: Aria-label
  if (await addBtn.count() === 0) {
    addBtn = card.locator('button[aria-label*="Добавить"], button[aria-label*="Add"]');
  }

  // СТРАТЕГИЯ 3: По символу плюс
  if (await addBtn.count() === 0) {
    addBtn = card.locator('button').filter({ hasText: /\+/ });
  }

  // СТРАТЕГИЯ 4: Последняя enabled кнопка (fallback)
  if (await addBtn.count() === 0) {
    const buttons = card.locator('button:not([disabled])');
    addBtn = buttons.last();
  }

  // Клик
  if (await addBtn.count() > 0) {
    await addBtn.click();
  } else {
    throw new Error('No add button found in product card');
  }

  return 'Add button clicked';
}
```

---

**ANTI-PATTERN (типичная ошибка):**

❌ **Ошибка: Слепое использование .first()**
```javascript
// ❌ ПЛОХО - попадаешь на disabled минус
const btn = card.locator('button').first();
await btn.click();  // TimeoutError!
```

❌ **Ошибка: JS click в evaluate без проверки состояния**
```javascript
// ❌ ПЛОХО - обходит disabled check, но click БЕЗ ЭФФЕКТА
await page.evaluate(() => {
  const btn = document.querySelector('button');  // Это disabled минус!
  btn.click();  // Сработает, но ничего не изменится
});
```

✅ **ПРАВИЛЬНО:**
```javascript
// ✅ Явный выбор кнопки плюс
await card.locator('button').filter({ hasText: '+' }).click();
// или
await card.locator('button:not([disabled])').last().click();
```

---

**Применяется к:**
- E-commerce сайты (Яндекс Лавка, Amazon, eBay)
- Корзины покупок
- Quantity pickers
- Любые UI компоненты со счетчиками

**Ключевой insight:** В счетчиках **позиция имеет значение**. Всегда выбирай кнопку по **семантике** (data-атрибуты, aria-label, текст), **НЕ по позиции** (.first()).

---

#### Click Methods: Playwright vs JavaScript

**КРИТИЧЕСКАЯ РАЗНИЦА** между двумя способами кликов:

**Playwright Click (РЕКОМЕНДУЕТСЯ):**
```javascript
// ✅ Триггерит ПОЛНЫЙ event flow (как реальный пользователь)
await locator.click()
```

**JavaScript Click (ОГРАНИЧЕННОЕ ПРИМЕНЕНИЕ):**
```javascript
// ⚠️ Обходит React/Vue/Angular event handlers
await page.evaluate(() => {
  el.click()  // Может НЕ сработать на SPA!
})
```

---

**ПОЧЕМУ это важно:**

Современные SPA (React, Vue, Angular) используют **синтетическую систему событий**:

```
Реальный клик → Browser Event → Framework Handlers → State Update → UI Re-render

JS click в evaluate() → Только Browser Event → ❌ Handlers НЕ вызваны
```

**Результат JS клика на SPA:**
- ❌ State НЕ обновляется (корзина остается пустой)
- ❌ Callbacks НЕ выполняются (запрос к API не отправлен)
- ❌ UI НЕ перерисовывается (count не меняется)

---

**КОГДА ИСПОЛЬЗОВАТЬ КАЖДЫЙ МЕТОД:**

✅ **Playwright click - ОСНОВНОЙ способ (99% случаев):**
```javascript
async (page) => {
  // Для ЛЮБЫХ интерактивных элементов на SPA
  await page.getByRole('button', { name: 'Add to cart' }).click();
  await page.locator('.product button').first().click();

  // Playwright автоматически:
  // - Ждет элемент (до 30 сек)
  // - Скроллит к элементу
  // - Проверяет visibility, enabled, stability
  // - Триггерит ВСЕ event handlers

  return 'Clicked successfully';
}
```

⚠️ **JS click - ТОЛЬКО для edge cases:**
```javascript
async (page) => {
  // ТОЛЬКО ЕСЛИ:
  // 1. Playwright click timeout (element outside viewport)
  // 2. Element covered by overlay
  // 3. После проверки что Playwright click НЕ работает

  await page.evaluate(() => {
    const btn = document.querySelector('.problem-button');
    if (btn) btn.click();
  });

  // WARNING: НЕ ГАРАНТИРУЕТ что click имел эффект!
  // ОБЯЗАТЕЛЬНО делай verification после!

  return 'JS click executed (verify state change!)';
}
```

---

**ДИАГНОСТИЧЕСКИЙ АЛГОРИТМ при проблемах с кликом:**

**Шаг 1: Попробуй Playwright click**
```javascript
try {
  await locator.click({ timeout: 5000 });
} catch (e) {
  // Переходи к Шагу 2
}
```

**Шаг 2: Проверь actionability**
```javascript
const isVisible = await locator.isVisible();
const isEnabled = await locator.isEnabled();

if (!isVisible) {
  await locator.scrollIntoViewIfNeeded();
}
```

**Шаг 3: Проверь модалки/overlays**
```javascript
const modals = await page.locator('dialog, [role="dialog"]').count();
if (modals > 0) {
  // Закрой модалки СНАЧАЛА
}
```

**Шаг 4: Force click (обход actionability checks)**
```javascript
await locator.click({ force: true });
// Используй force ТОЛЬКО если понимаешь риски
```

**Шаг 5: JS click (последний резерв)**
```javascript
await page.evaluate(() => {
  document.querySelector('.btn').click();
});
```

**Шаг 6: ОБЯЗАТЕЛЬНАЯ verification после любого клика**
```javascript
// Запомни состояние ДО
const countBefore = await page.locator('.cart-count').textContent();

// Клик (любым способом)
await locator.click();

// Подожди изменения
await page.waitForTimeout(1000);

// Проверь состояние ПОСЛЕ
const countAfter = await page.locator('.cart-count').textContent();

if (countBefore === countAfter) {
  throw new Error('Click had NO effect - state unchanged!');
}
```

---

**ANTI-PATTERN (типичная ошибка):**

❌ **НЕ делай так:**
```javascript
// ОШИБКА: JS click БЕЗ verification
await page.evaluate(() => {
  document.querySelector('button').click();
});

// Предполагаешь успех - НО ничего не изменилось!
return 'Items added to cart';  // ❌ ЛОЖь!
```

✅ **Делай так:**
```javascript
// Playwright click + verification
await page.locator('button').click();

// ПРОВЕРЬ что click имел эффект
const cartCount = await page.locator('.cart-count').textContent();
const parsedCount = parseInt(cartCount);

if (parsedCount === 0) {
  throw new Error('Click success BUT cart still empty - try different approach');
}

return `Verified: ${parsedCount} items in cart`;  // ✓ ПРАВДА
```

---

**Клик по элементу:**
```javascript
async (page) => {
  await page.getByRole('button', { name: 'Submit' }).click();
  return 'Button clicked';
}
```

**Ввод текста:**
```javascript
async (page) => {
  // fill - заменяет текст полностью
  await page.getByPlaceholder('Email').fill('user@example.com');

  // type - печатает посимвольно (медленнее, но имитирует пользователя)
  await page.getByPlaceholder('Password').type('password123');

  return 'Text entered';
}
```

**Нажатие клавиши:**
```javascript
async (page) => {
  await page.getByPlaceholder('Search').fill('playwright');
  await page.getByPlaceholder('Search').press('Enter');

  // Или комбинация клавиш
  await page.keyboard.press('Control+A');

  return 'Key pressed';
}
```

**Выбор в select (dropdown):**
```javascript
async (page) => {
  // По значению
  await page.locator('select#country').selectOption('russia');

  // По видимому тексту
  await page.locator('select#country').selectOption({ label: 'Russia' });

  // По индексу
  await page.locator('select#country').selectOption({ index: 2 });

  return 'Option selected';
}
```

**Checkbox и radio buttons:**
```javascript
async (page) => {
  // Отметить checkbox
  await page.getByLabel('I agree to terms').check();

  // Снять отметку
  await page.getByLabel('Subscribe to newsletter').uncheck();

  // Radio button
  await page.getByRole('radio', { name: 'Male' }).check();

  return 'Checkbox/radio updated';
}
```

**Hover (наведение мыши):**
```javascript
async (page) => {
  await page.getByRole('button', { name: 'Menu' }).hover();
  return 'Hovered over menu button';
}
```

---

### Извлечение данных

**Helper функция для очистки текста от спецсимволов:**
```javascript
// Очистить текст от невидимых Unicode символов (Gmail добавляет их защиты от парсеров)
function cleanText(text) {
  if (!text) return text;
  return text
    .replace(/\u200c/g, '')        // Zero-width non-joiner
    .replace(/\u200b/g, '')        // Zero-width space
    .replace(/\u200d/g, '')        // Zero-width joiner
    .replace(/\xa0/g, ' ')         // Non-breaking space → обычный пробел
    .replace(/\s+/g, ' ')          // Множественные пробелы → один
    .trim();
}
```

**Текст элемента (с очисткой):**
```javascript
async (page) => {
  function cleanText(text) {
    if (!text) return text;
    return text
      .replace(/\u200c/g, '')
      .replace(/\u200b/g, '')
      .replace(/\u200d/g, '')
      .replace(/\xa0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const title = await page.locator('h1').textContent();
  return cleanText(title);
}
```

**Извлечение из множественных элементов (с очисткой):**
```javascript
async (page) => {
  function cleanText(text) {
    if (!text) return text;
    return text
      .replace(/\u200c/g, '')
      .replace(/\u200b/g, '')
      .replace(/\u200d/g, '')
      .replace(/\xa0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const items = page.locator('.product-item');
  const count = await items.count();

  const products = [];
  // ВАЖНО: Извлекай СТОЛЬКО элементов, СКОЛЬКО нужно для задачи
  // Для поиска конкретного товара - достаточно первых 20-30
  // Для сбора полного каталога - извлекай ВСЕ (count)
  // Для выбора лучшей цены - извлекай ВСЕ с ценами (count)
  const limit = count;  // По умолчанию - ВСЕ элементы

  for (let i = 0; i < Math.min(count, limit); i++) {
    const name = await items.nth(i).locator('.name').textContent();
    const price = await items.nth(i).locator('.price').textContent();
    products.push({
      name: cleanText(name),
      price: cleanText(price)
    });
  }

  return JSON.stringify(products);
}
```

**Получение атрибутов:**
```javascript
async (page) => {
  // Одиночный атрибут
  const href = await page.locator('a.download').getAttribute('href');

  // Значение input
  const inputValue = await page.locator('input#email').inputValue();

  // Проверка наличия класса
  const hasClass = await page.locator('button').evaluate((el) =>
    el.classList.contains('active')
  );

  return JSON.stringify({ href, inputValue, hasClass });
}
```

**Информация о странице:**
```javascript
async (page) => {
  const url = page.url();
  const title = await page.title();

  return JSON.stringify({ url, title });
}
```

---

### Ожидание (Waiting)

**Автоматическое ожидание (встроено в Playwright):**
```javascript
async (page) => {
  // Playwright автоматически ждет до 30 сек перед действиями
  await page.getByText('Welcome').click();  // Ждет появления элемента

  return 'Element clicked (auto-waited)';
}
```

**Явное ожидание элемента:**
```javascript
async (page) => {
  // Ждать появления селектора
  await page.waitForSelector('.results', { timeout: 10000 });

  // Или через локатор
  await page.locator('.results').waitFor({ state: 'visible', timeout: 10000 });

  return 'Element appeared';
}
```

**Ожидание загрузки страницы:**
```javascript
async (page) => {
  await page.goto('https://example.com');

  // Разные состояния:
  await page.waitForLoadState('load');         // DOM загружен
  await page.waitForLoadState('domcontentloaded'); // HTML распарсен
  await page.waitForLoadState('networkidle');  // Нет сетевых запросов 500мс

  return 'Page fully loaded';
}
```

**Ожидание навигации:**
```javascript
async (page) => {
  // Ждать переход на другую страницу после клика
  await Promise.all([
    page.waitForNavigation(),
    page.getByRole('button', { name: 'Submit' }).click()
  ]);

  return 'Navigation completed';
}
```

---

### Скроллинг

**Скролл к элементу:**
```javascript
async (page) => {
  // Playwright автоматически скроллит к элементу перед действием
  await page.getByText('Footer').scrollIntoViewIfNeeded();

  return 'Scrolled to footer';
}
```

**Скролл страницы:**
```javascript
async (page) => {
  // Скролл на N пикселей
  await page.evaluate(() => window.scrollBy(0, 500));

  // Скролл в конец страницы
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

  return 'Page scrolled';
}
```

---

### Работа с iframe

**Доступ к элементам внутри iframe:**
```javascript
async (page) => {
  // Современный способ (рекомендуется)
  const frame = page.frameLocator('iframe#content');
  await frame.getByRole('button', { name: 'Click me' }).click();

  return 'Clicked button inside iframe';
}
```

---

### Скриншоты

**Скриншот всей страницы:**
```javascript
async (page) => {
  const screenshot = await page.screenshot({
    fullPage: true,
    type: 'png'
  });

  return `Screenshot taken: ${screenshot.length} bytes`;
}
```

**Скриншот конкретного элемента:**
```javascript
async (page) => {
  const element = page.getByRole('button', { name: 'Submit' });
  await element.screenshot({ path: 'button.png' });

  return 'Element screenshot saved to button.png';
}
```

---

### Обработка ошибок

**Проверка существования элемента:**
```javascript
async (page) => {
  const button = page.getByRole('button', { name: 'Submit' });

  // Проверить количество найденных элементов
  const count = await button.count();
  if (count === 0) {
    throw new Error('Submit button not found');
  }

  await button.click();
  return 'Button clicked';
}
```

**Условное ожидание (try-catch):**
```javascript
async (page) => {
  try {
    // Попробовать найти сообщение об ошибке
    await page.waitForSelector('.error-message', { timeout: 5000 });
    const errorText = await page.locator('.error-message').textContent();
    return `Error found: ${errorText}`;
  } catch (e) {
    // Ошибка не найдена - это нормально
    return 'No error message';
  }
}
```

**Безопасное извлечение данных:**
```javascript
async (page) => {
  const titleLocator = page.locator('h1');

  // Безопасно получить текст (с fallback)
  const title = (await titleLocator.textContent()) || 'No title';

  return title.trim();
}
```

---

### Выполнение JavaScript на странице

**Простое выполнение:**
```javascript
async (page) => {
  // Выполнить JS и получить результат
  const result = await page.evaluate(() => {
    return document.querySelectorAll('a').length;
  });

  return `Found ${result} links`;
}
```

**С передачей аргументов:**
```javascript
async (page) => {
  const selector = '.product';
  const count = await page.evaluate((sel) => {
    return document.querySelectorAll(sel).length;
  }, selector);

  return `Found ${count} products`;
}
```

---

### Ключевые правила и best practices

1. **Всегда используй современные локаторы** (getByRole, getByText, getByPlaceholder) вместо CSS селекторов где возможно - они более надежные и читаемые

2. **Playwright автоматически ждет** - в большинстве случаев не нужен явный wait. Локаторы ждут до 30 секунд по умолчанию

3. **ДЛЯ SPA: ВСЕГДА жди изменения DOM после взаимодействия** - клик может загружать контент асинхронно. Используй waitFor(), waitForFunction() или проверяй изменение count() элементов

4. **Проверяй что контент действительно загрузился** - после клика по категории/фильтру/кнопке убедись что новые элементы появились (count > 0)

5. **Используй async/await** для всех операций с page - все методы асинхронные

6. **Возвращай понятный результат** последней строкой функции - это то, что увидишь в response

7. **Для сложных данных используй JSON.stringify()** - это гарантирует корректную сериализацию

8. **ВСЕГДА очищай извлеченный текст через cleanText()** - веб-страницы (особенно Gmail, соцсети) добавляют невидимые Unicode символы (\u200c, \u200b, \xa0) для защиты от парсеров. cleanText() удаляет их и нормализует пробелы

9. **Обрабатывай ошибки** - проверяй существование элементов через count() перед взаимодействием

10. **Для вкладок используй page.context().pages()** - это массив с 0-based индексами (первая вкладка = index 0)

11. **ДЛЯ SPA: НЕ используй долгие waitForLoadState('networkidle')** - современные SPA делают фоновые запросы бесконечно. Вместо этого жди КОНКРЕТНЫЕ элементы с коротким timeout (5-10 сек). Только для обычных сайтов можно использовать networkidle с timeout: 10000

12. **Избегай фиксированных задержек** - используй их только как последнее средство для нестабильных SPA. Предпочитай waitFor() с проверкой конкретного условия

13. **Для множественных элементов используй count() и nth()** - не полагайся на индексацию через CSS nth-child

14. **Если элементы не найдены после действия** - возможно контент загружается динамически. Добавь явное ожидание появления или используй waitForFunction()

---

### Частые ошибки и как их избежать

❌ **НЕ делай так:**
```javascript
// КРИТИЧЕСКАЯ ОШИБКА: getByRole() с массивом
page.getByRole(['button', 'link'])  // InvalidSelectorError!
// getByRole() принимает ТОЛЬКО строку, НЕ массив!

// Забыл await
page.getByRole('button').click();  // Не сработает!

// Использование старых селекторов без причины
page.locator('button').click();  // Лучше getByRole

// Фиксированная задержка
await page.waitForTimeout(3000);  // Антипаттерн!

// ДОЛГОЕ ожидание networkidle для SPA (ОЧЕНЬ МЕДЛЕННО)
await page.waitForLoadState('networkidle', { timeout: 60000 });  // Может ждать минуту!
// SPA делают бесконечные фоновые запросы - networkidle не наступит

// Не проверил существование
const text = await page.locator('.missing').textContent();  // Может упасть

// НЕ очистил текст от спецсимволов
const email = await page.locator('.sender').textContent();
// Получишь: "example.com\xa0\u200c\u200c\u200c"
```

✅ **Делай так:**
```javascript
// Для МНОЖЕСТВЕННЫХ типов элементов - locator() с CSS селектором
const buttonsAndLinks = page.locator('button, a, [role="button"], [role="link"]');

// Для ОДНОГО типа - getByRole()
const onlyButtons = page.getByRole('button');

// Всегда await
await page.getByRole('button', { name: 'Submit' }).click();

// Современные локаторы
await page.getByRole('button', { name: 'Submit' }).click();

// ДЛЯ SPA: жди КОНКРЕТНЫЕ элементы с коротким timeout (БЫСТРО)
await page.locator('.product-card').first().waitFor({ state: 'visible', timeout: 5000 });
// Или проверяй изменение count()
await page.waitForFunction(
  () => document.querySelectorAll('.product').length > 0,
  { timeout: 5000 }
);

// Для обычных сайтов: короткий timeout на networkidle
await page.waitForLoadState('networkidle', { timeout: 10000 });  // Макс 10 сек

// Проверка существования
const locator = page.locator('.optional');
if (await locator.count() > 0) {
  const text = await locator.textContent();
}

// ВСЕГДА очищай извлеченный текст
function cleanText(text) {
  if (!text) return text;
  return text.replace(/\u200c/g, '').replace(/\u200b/g, '')
             .replace(/\u200d/g, '').replace(/\xa0/g, ' ')
             .replace(/\s+/g, ' ').trim();
}
const email = cleanText(await page.locator('.sender').textContent());
// Получишь: "example.com" - чистый текст!
```

---

### 🚨 КРИТИЧНЫЕ СИНТАКСИЧЕСКИЕ ОШИБКИ (ЧАСТО ПОВТОРЯЕМЫЕ)

**ВАЖНО:** Эти ошибки приводят к немедленному падению кода. Проверяй свой код на эти паттерны!

#### Ошибка #1: Неверный синтаксис CSS селектора в locator()

❌ **НИКОГДА НЕ ДЕЛАЙ:**
```javascript
// ОШИБКА: запятая БЕЗ кавычек внутри locator() - InvalidSelectorError!
page.locator('button, [role="button"]')
//           ^^^^^^ это CSS селектор - запятая означает ИЛИ,
//           НО первая кавычка закрывается после button!

// Реальная ошибка: page.getByRole('button, [role="button"]').filter(...)
// Playwright видит: getByRole('button, [role=')  <-- обрезано!
```

✅ **ПРАВИЛЬНО:**
```javascript
// Вариант 1: Используй locator() ТОЛЬКО с полным CSS
page.locator('button, a, [role="button"], [role="link"]')  // Корректный CSS

// Вариант 2: getByRole() для одной роли
page.getByRole('button')  // Только кнопки

// Вариант 3: filter() для комбинаций
page.locator('button, a').filter({ hasText: /напит/i })  // OK!
```

#### Ошибка #2: Массив вместо строки в getByRole()

❌ **НИКОГДА НЕ ДЕЛАЙ:**
```javascript
// КРИТИЧЕСКАЯ ОШИБКА: getByRole() принимает ТОЛЬКО строку!
page.getByRole(['button', 'link'])      // TypeError!
page.getByRole([...])                   // ВСЕГДА падает!
```

✅ **ПРАВИЛЬНО:**
```javascript
// ТОЛЬКО ОДНА роль за раз
page.getByRole('button')
page.getByRole('link')

// Для нескольких типов - используй locator()
page.locator('button, a, [role="button"]')
```

#### Ошибка #3: Неправильные скобки для async/await с slice()

❌ **НИКОГДА НЕ ДЕЛАЙ:**
```javascript
// ОШИБКА: slice() вызывается на Promise, а не на array!
const items = await page.getByRole('button').allTextContents().slice(0, 10);
//            ^^^^^ await здесь ждет Promise от allTextContents()
//                                                            ^^^^^^^ НО slice вызывается ДО await!
// Результат: TypeError: Promise.slice is not a function
```

✅ **ПРАВИЛЬНО:**
```javascript
// Обернуть allTextContents() в скобки!
const items = (await page.getByRole('button').allTextContents()).slice(0, 10);
//            ^                                                  ^
//            скобки гарантируют: await сначала, потом slice()
```

**Правило:** Для любого метода, возвращающего Promise<Array>, ВСЕГДА оборачивай в скобки перед array методами:
```javascript
// ✅ Правильно:
(await locator.allTextContents()).slice(0, 5)
(await locator.allTextContents()).filter(x => x.length > 0)
(await locator.allTextContents()).map(cleanText)

// ❌ Неправильно:
await locator.allTextContents().slice(0, 5)      // ОШИБКА!
await locator.allTextContents().filter(...)      // ОШИБКА!
```

#### Ошибка #4: Использование networkidle для SPA

❌ **НИКОГДА НЕ ДЕЛАЙ (для SPA):**
```javascript
// ОШИБКА: SPA делают бесконечные фоновые запросы - networkidle может НИКОГДА не наступить!
await page.goto('https://lavka.yandex.ru/', { waitUntil: 'networkidle', timeout: 30000 });
//                                                        ^^^^^^^^^^^^
// Яндекс Лавка, Gmail, соцсети - всё это SPA с метриками, WebSocket, polling
// Timeout после 30 секунд, но страница уже загрузилась за 2 секунды!
```

✅ **ПРАВИЛЬНО (для SPA):**
```javascript
// Вариант 1: domcontentloaded (БЫСТРО)
await page.goto('https://lavka.yandex.ru/', { waitUntil: 'domcontentloaded', timeout: 15000 });
// DOM готов за 1-3 секунды обычно

// Вариант 2: domcontentloaded + ждать конкретный элемент
await page.goto('https://example.com/', { waitUntil: 'domcontentloaded' });
await page.locator('.product-card').first().waitFor({ state: 'visible', timeout: 5000 });

// Для обычных статичных сайтов networkidle OK, но с коротким timeout:
await page.goto('https://example.org/', { waitUntil: 'networkidle', timeout: 10000 });
```

#### Ошибка #5: waitForFunction() с неправильным синтаксисом селектора

❌ **НИКОГДА НЕ ДЕЛАЙ:**
```javascript
// ОШИБКА: двойной {} - второй объект должен быть опции, не пустой!
await page.waitForFunction(
  () => document.querySelectorAll('.product').length > 0,
  {},          // <-- ОШИБКА: это должны быть args для функции, не options!
  { timeout: 10000 }  // <-- options здесь игнорируются
);
```

✅ **ПРАВИЛЬНО:**
```javascript
// Без аргументов - передать null, затем options
await page.waitForFunction(
  () => document.querySelectorAll('.product').length > 0,
  null,
  { timeout: 5000 }
);

// С аргументами - передать их, затем options (опционально)
await page.waitForFunction(
  (sel) => document.querySelectorAll(sel).length > 0,
  '.product',
  { timeout: 5000 }
);
```

#### Ошибка #6: Клик на элемент outside viewport без scroll

❌ **НИКОГДА НЕ ДЕЛАЙ:**
```javascript
// ОШИБКА: элемент вне viewport - click() упадет с timeout
const skipBtn = page.locator('button:has-text("Пропустить")').first();
await skipBtn.click();  // TimeoutError: Element is outside of the viewport
```

✅ **ПРАВИЛЬНО:**
```javascript
// Вариант 1: scrollIntoViewIfNeeded перед кликом
const skipBtn = page.locator('button:has-text("Пропустить")').first();
if (await skipBtn.count() > 0) {
  await skipBtn.scrollIntoViewIfNeeded();
  await skipBtn.click();
}

// Вариант 2: force click (обходит проверки viewport)
await skipBtn.click({ force: true });

// Вариант 3: JS клик (для особо сложных случаев)
await page.evaluate(() => {
  const btn = document.querySelector('button');
  if (btn) btn.click();
});
```

---

### СТРАТЕГИЯ РАБОТЫ С POPUP/MODAL

**Проблема:** Popup/Modal окна часто блокируют контент и требуют закрытия. НО accessibility элементы (skip-to-content) тоже содержат текст "Пропустить", но НЕ являются popup!

**Алгоритм (пошагово):**

**Шаг 1: Идентифицировать настоящий popup**
```javascript
// Настоящие popup имеют семантические роли или классы
const popups = page.locator('dialog, [role="dialog"], .Modal, .popup, [class*="modal"], [class*="Popup"]');
const popupCount = await popups.count();

if (popupCount === 0) {
  return 'No popups found';  // Ничего не делать!
}
```

**Шаг 2: Проверить видимость popup**
```javascript
const isVisible = await popups.first().isVisible();
if (!isVisible) {
  return 'Popup exists but hidden';  // Не трогать!
}
```

**Шаг 3: Найти кнопку закрытия ВНУТРИ popup**
```javascript
// ✅ ПРАВИЛЬНО: искать ТОЛЬКО внутри dialog
const closeBtn = popups.first().locator('button:has-text("Закрыть"), button:has-text("Пропустить"), button[aria-label*="закрыть"], .close-button, [data-testid*="close"]');

// ❌ НЕПРАВИЛЬНО: глобальный поиск - найдет accessibility элементы!
const wrongBtn = page.locator('button:has-text("Пропустить")');
```

**Шаг 4: Безопасный клик с обработкой viewport**
```javascript
if (await closeBtn.count() > 0) {
  try {
    await closeBtn.first().scrollIntoViewIfNeeded();
    await closeBtn.first().click({ timeout: 5000 });
  } catch (e) {
    // Если viewport проблема - fallback на JS click
    await page.evaluate(() => {
      const modal = document.querySelector('dialog, [role="dialog"]');
      if (modal) {
        const btn = modal.querySelector('button');
        if (btn) btn.click();
      }
    });
  }
}
```

**Шаг 5: Verify закрытие**
```javascript
// Подождать исчезновения popup
await popups.first().waitFor({ state: 'hidden', timeout: 3000 });
return 'Popup closed successfully';
```

**Полный пример для Яндекс Лавки (popup с выбором адреса):**
```javascript
async (page) => {
  // 1. Проверить наличие popup
  const modals = page.locator('dialog, [role="dialog"], .Modal');
  if (await modals.count() === 0) {
    return 'No modal to handle';
  }

  // 2. Это popup с адресом - кликнуть на сам адрес для подтверждения (НЕ "Пропустить"!)
  const addressBtn = page.getByRole('button').filter({ hasText: /Main|Street|адрес/i });
  if (await addressBtn.count() > 0) {
    // JS клик для обхода viewport (адрес может быть вне viewport)
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Main Street') || b.textContent.includes('street'));
      if (btn) btn.click();
    });

    // Подождать закрытия modal
    await page.waitForTimeout(2000);  // SPA нужно время на transition
    return 'Address selected, modal closed';
  }

  // 3. Fallback: найти кнопку закрытия внутри modal
  const closeBtn = modals.first().locator('button:has-text("Закрыть"), [aria-label*="закрыть"]');
  if (await closeBtn.count() > 0) {
    await closeBtn.click({ force: true });
    await modals.first().waitFor({ state: 'hidden', timeout: 3000 });
    return 'Modal closed via close button';
  }

  return 'Modal found but no way to close';
}
```

**Ключевые правила для popup:**
1. ВСЕГДА используй семантические селекторы (dialog, [role="dialog"]) для идентификации
2. НИКОГДА не ищи кнопки глобально - только внутри popup с `.locator()`
3. Проверяй isVisible() перед взаимодействием
4. Для SPA popup: добавляй waitForTimeout(1000-2000) после клика для анимации
5. Если viewport error - используй page.evaluate() JS клик
6. Verify закрытие через waitFor({ state: 'hidden' })

---

### Работа с динамическим контентом (SPA)

**ВАЖНО:** Современные веб-приложения часто используют динамическую загрузку контента без перезагрузки страницы.

**Ожидание появления контента после взаимодействия:**
```javascript
async (page) => {
  // Клик по элементу, который загружает контент
  await page.getByRole('button', { name: 'Load More' }).click();

  // Ждать появления НОВОГО контента
  await page.locator('.new-item').first().waitFor({ state: 'visible', timeout: 10000 });

  // Теперь безопасно извлекать данные
  const items = page.locator('.new-item');
  const count = await items.count();

  return `Loaded ${count} new items`;
}
```

**Проверка изменений DOM после клика:**
```javascript
async (page) => {
  // Запомнить начальное состояние
  const initialCount = await page.locator('.item').count();

  // Выполнить действие
  await page.getByRole('button', { name: 'Filter' }).click();

  // Подождать изменения DOM
  await page.waitForFunction(
    (initial) => document.querySelectorAll('.item').length !== initial,
    initialCount,
    { timeout: 5000 }
  );

  const newCount = await page.locator('.item').count();
  return `Items changed from ${initialCount} to ${newCount}`;
}
```

**Ожидание завершения AJAX запросов:**
```javascript
async (page) => {
  await page.getByRole('button', { name: 'Search' }).click();

  // Ждать когда сеть успокоится
  await page.waitForLoadState('networkidle', { timeout: 10000 });

  // Или ждать исчезновения спиннера
  const spinner = page.locator('.loading-spinner');
  if (await spinner.count() > 0) {
    await spinner.waitFor({ state: 'hidden', timeout: 10000 });
  }

  return 'Content loaded';
}
```

**Обработка модальных окон и оверлеев:**
```javascript
async (page) => {
  // Проверить наличие модального окна
  const modal = page.locator('dialog, [role="dialog"], .modal');
  const modalCount = await modal.count();

  if (modalCount > 0 && await modal.isVisible()) {
    // Модальное окно открыто - взаимодействовать с ним
    const confirmBtn = modal.locator('button:has-text("OK"), button:has-text("Подтвердить")');
    if (await confirmBtn.count() > 0) {
      await confirmBtn.click();
      // Ждать закрытия модалки
      await modal.waitFor({ state: 'hidden', timeout: 5000 });
      return 'Modal confirmed and closed';
    }
  }

  return 'No modal found';
}
```

**Множественные попытки для нестабильных элементов:**
```javascript
async (page) => {
  let attempts = 0;
  const maxAttempts = 3;

  while (attempts < maxAttempts) {
    try {
      // Попробовать найти и кликнуть элемент
      await page.getByRole('button', { name: 'Submit' }).click({ timeout: 5000 });
      return 'Clicked successfully';
    } catch (e) {
      attempts++;
      if (attempts >= maxAttempts) {
        throw new Error(`Failed after ${maxAttempts} attempts: ${e.message}`);
      }
      // Подождать перед повтором
      await page.waitForTimeout(1000);
    }
  }
}
```

---

### Примеры типичных задач

**1. Заполнение и отправка формы:**
```javascript
async (page) => {
  await page.goto('https://example.com/login');
  await page.waitForLoadState('networkidle');

  await page.getByPlaceholder('Email').fill('user@example.com');
  await page.getByPlaceholder('Password').fill('password123');
  await page.getByRole('button', { name: 'Login' }).click();

  // Ждать навигации
  await page.waitForURL('**/dashboard');

  return 'Successfully logged in';
}
```

**2. Извлечение списка элементов:**
```javascript
async (page) => {
  function cleanText(text) {
    if (!text) return text;
    return text
      .replace(/\u200c/g, '')
      .replace(/\u200b/g, '')
      .replace(/\u200d/g, '')
      .replace(/\xa0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const items = page.locator('.product-card');
  const count = await items.count();

  const products = [];
  // Извлекай СТОЛЬКО, СКОЛЬКО нужно для задачи:
  // - Для preview/ознакомления: 10-20 элементов
  // - Для выбора по критериям (цена, название): ВСЕ элементы (count)
  // - Для сбора корзины/списка: ВСЕ подходящие (count)
  for (let i = 0; i < count; i++) {  // По умолчанию - ВСЕ
    const item = items.nth(i);
    const title = await item.locator('h3').textContent();
    const price = await item.locator('.price').textContent();
    products.push({
      title: cleanText(title),
      price: cleanText(price)
    });
  }

  return JSON.stringify(products);
}
```

**3. Работа с выпадающим меню:**
```javascript
async (page) => {
  // Открыть меню
  await page.getByRole('button', { name: 'Menu' }).click();

  // Ждать появления пункта меню
  const menuItem = page.getByRole('menuitem', { name: 'Settings' });
  await menuItem.waitFor({ state: 'visible' });

  // Кликнуть
  await menuItem.click();

  return 'Navigated to Settings';
}
```

**4. Проверка наличия текста на странице:**
```javascript
async (page) => {
  const searchText = 'Welcome';
  const found = await page.getByText(searchText).count() > 0;

  return found ? `Text "${searchText}" found` : `Text "${searchText}" not found`;
}
```

---

### Надежное извлечение данных через page.evaluate() в browser_run_code

**ВАЖНО:** `page.evaluate()` - это метод Playwright Page API, используемый **ВНУТРИ browser_run_code**.

**🎯 ПАТТЕРН: Page Structure Exploration (ПЕРВЫЙ ШАГ на новой странице)**

Перед любыми действиями - исследуй структуру страницы:

```javascript
async (page) => {
  const pageStructure = await page.evaluate(() => {
    // Универсальное исследование структуры
    return {
      // Навигация и категории
      hasCategories: document.querySelectorAll('nav a, [role="navigation"] a, .category, [class*="Category"]').length > 0,
      categoriesCount: document.querySelectorAll('nav a, [role="navigation"] a').length,

      // Поиск
      hasSearch: document.querySelectorAll('input[type="search"], input[placeholder*="поиск"], input[placeholder*="Найти"], .search-input').length > 0,
      searchButtonExists: document.querySelectorAll('button[aria-label*="поиск"], [class*="SearchButton"]').length > 0,

      // Контент
      hasProducts: document.querySelectorAll('article, .product, [class*="Product"], [data-testid*="product"]').length > 0,
      productsCount: document.querySelectorAll('article, .product').length,

      // Модалки
      hasModals: document.querySelectorAll('dialog, [role="dialog"], .Modal, [class*="modal"]').length > 0,

      // Какие элементы доступны
      availableElements: {
        buttons: document.querySelectorAll('button').length,
        links: document.querySelectorAll('a').length,
        inputs: document.querySelectorAll('input').length
      }
    };
  });

  return JSON.stringify(pageStructure);
}
```

**Используй этот паттерн для:**
- Понимания что доступно на странице ПЕРЕД действиями
- Выбора правильной стратегии (категории vs поиск vs меню)
- Избежания timeout из-за несуществующих элементов

---

**Когда использовать page.evaluate() вместо Playwright локаторов:**

1. **Playwright селекторы не находят элементы** - классы/id динамические
2. **Timeout при извлечении textContent()** - элементы загружаются асинхронно
3. **Нужно извлечь ВСЕ данные быстро** - evaluate работает синхронно в браузере
4. **Сложная логика фильтрации** - проще написать JS чем цепочку Playwright методов

**Паттерн: Массовое извлечение данных продуктов/товаров:**

Полный вызов browser_run_code с page.evaluate() внутри:

```javascript
// ВСЁ ЭТО - КОД ДЛЯ browser_run_code
async (page) => {
  // page.evaluate() - МЕТОД Page API, выполняет JS в браузере
  const productsData = await page.evaluate(() => {
    function cleanText(text) {
      if (!text) return '';
      return text.replace(/[\u200B-\u200D\uFEFF\xA0]/g, ' ')
                 .replace(/\s+/g, ' ')
                 .trim();
    }

    // Множественные селекторы для универсальности
    const items = document.querySelectorAll(
      '.product, .product-card, article, [data-testid*="product"], [class*="item"], [class*="good"]'
    );

    const products = [];

    for (let item of items) {
      // Попробовать разные варианты селекторов для имени
      const nameEl = item.querySelector('h1, h2, h3, h4, [class*="name"], [class*="title"], [class*="header"]');
      const name = nameEl ? cleanText(nameEl.textContent) : '';

      // Попробовать разные варианты селекторов для цены
      const priceEl = item.querySelector('[class*="price"], .Price, [data-auto*="price"], [class*="cost"]');
      const price = priceEl ? cleanText(priceEl.textContent) : '';

      // Кнопка добавления
      const addBtn = item.querySelector('button, [role="button"]');
      const hasAddButton = !!addBtn;

      // Включить только элементы с данными
      if (name && price) {
        products.push({ name, price, hasAddButton });
      }
    }

    return products;  // Вернуть ВСЕ найденные продукты
  });

  return JSON.stringify(productsData);
}
```

**Преимущества page.evaluate() подхода:**

1. ✅ **Не нужен await для каждого элемента** - всё выполняется синхронно в браузере
2. ✅ **Нет timeout ошибок** - данные уже в DOM, просто извлекаем
3. ✅ **Гибкие селекторы** - можно использовать любой JS для поиска
4. ✅ **Быстрее** - один evaluate вместо N * (nth + locator + textContent)
5. ✅ **Чистка данных сразу** - cleanText применяется в том же контексте

**Когда page.evaluate() НЕ подходит:**

- ❌ Элементы еще не загрузились в DOM (нужен waitFor сначала)
- ❌ Нужно взаимодействовать (клик, ввод) - только для чтения данных
- ❌ Работа с iframe - evaluate работает только в текущем контексте

**ЗАПОМНИ:** Все эти примеры - это код для **browser_run_code**! Инструмент всегда один - browser_run_code.

**Комбинированный паттерн (сначала wait, потом evaluate):**

```javascript
async (page) => {
  // 1. Дождаться появления ХОТЯ БЫ ОДНОГО элемента
  await page.locator('.product, article').first().waitFor({
    state: 'visible',
    timeout: 10000
  }).catch(() => {});  // Игнорировать timeout - попробуем извлечь что есть

  // 2. Извлечь ВСЕ через evaluate (даже если waitFor не сработал)
  const productsData = await page.evaluate(() => {
    function cleanText(text) {
      if (!text) return '';
      return text.replace(/[\u200B-\u200D\uFEFF\xA0]/g, ' ')
                 .replace(/\s+/g, ' ')
                 .trim();
    }

    const items = document.querySelectorAll('.product, article, [class*="product"]');
    const products = [];

    for (let item of items) {
      const name = item.querySelector('h1, h2, h3, [class*="name"]')?.textContent || '';
      const price = item.querySelector('[class*="price"]')?.textContent || '';

      if (name && price) {
        products.push({
          name: cleanText(name),
          price: cleanText(price)
        });
      }
    }

    return products;
  });

  // 3. Проверить результат
  if (productsData.length === 0) {
    throw new Error('No products found after waiting and evaluate');
  }

  return JSON.stringify(productsData);
}
```

**Извлечение данных с фильтрацией в JS:**

```javascript
async (page) => {
  const drinksData = await page.evaluate(() => {
    function cleanText(t) {
      return t ? t.replace(/[\u200B-\u200D\uFEFF\xA0]/g, ' ').replace(/\s+/g, ' ').trim() : '';
    }

    const items = document.querySelectorAll('.product, article');
    const drinks = [];

    for (let item of items) {
      const name = cleanText(item.querySelector('h1, h2, h3, [class*="name"]')?.textContent || '');
      const price = cleanText(item.querySelector('[class*="price"]')?.textContent || '');

      // Фильтрация в JS - БЫСТРЕЕ чем в Playwright
      const isDrink = /вода|сок|кола|напиток|пиво|лимонад/i.test(name);

      if (name && price && isDrink) {
        drinks.push({ name, price });
      }
    }

    return drinks;
  });

  return JSON.stringify(drinksData);
}
```

**Ключевые правила использования evaluate:**

1. **cleanText функция ВНУТРИ evaluate** - не доступна снаружи
2. **Возвращай простые объекты** - не DOM элементы (не сериализуются)
3. **Используй optional chaining** `?.` - элемент может не существовать
4. **Всегда проверяй результат** - если массив пустой, возможно селекторы неправильные

Используй эти паттерны как основу для всех операций с браузером!
"""
