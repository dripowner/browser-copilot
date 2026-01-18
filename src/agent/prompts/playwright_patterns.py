"""Playwright Page API patterns for browser_run_code tool.

This module provides comprehensive guide on using Playwright Page API
through the browser_run_code tool. All browser operations must use this
single tool with Playwright code.
"""

PLAYWRIGHT_PATTERNS = """## Playwright Page API Patterns

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
  await page.goto('https://example.com');
  await page.waitForLoadState('networkidle');  // Ждать завершения всех запросов
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

**Современные локаторы (РЕКОМЕНДУЕТСЯ - accessibility-first):**
```javascript
async (page) => {
  // По ARIA роли
  const submitBtn = page.getByRole('button', { name: 'Submit' });

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

**CSS/XPath селекторы (если необходимо):**
```javascript
async (page) => {
  // CSS селекторы
  const element = page.locator('button.submit');
  const byId = page.locator('#email-input');
  const byClass = page.locator('.error-message');

  // XPath (редко нужно)
  const byXPath = page.locator('xpath=//button[@type="submit"]');

  return 'CSS/XPath locators created';
}
```

---

### Взаимодействие с элементами

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

**Текст элемента:**
```javascript
async (page) => {
  const title = await page.locator('h1').textContent();
  return title.trim();
}
```

**Извлечение из множественных элементов:**
```javascript
async (page) => {
  const items = page.locator('.product-item');
  const count = await items.count();

  const products = [];
  for (let i = 0; i < count; i++) {
    const name = await items.nth(i).locator('.name').textContent();
    const price = await items.nth(i).locator('.price').textContent();
    products.push({ name: name.trim(), price: price.trim() });
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

3. **Используй async/await** для всех операций с page - все методы асинхронные

4. **Возвращай понятный результат** последней строкой функции - это то, что увидишь в response

5. **Для сложных данных используй JSON.stringify()** - это гарантирует корректную сериализацию

6. **Обрабатывай ошибки** - проверяй существование элементов через count() перед взаимодействием

7. **Для вкладок используй page.context().pages()** - это массив с 0-based индексами (первая вкладка = index 0)

8. **Проверяй состояние загрузки** - используй waitForLoadState('networkidle') после навигации

9. **Не используй фиксированные задержки** - Playwright автоматически ждет, page.waitForTimeout() - антипаттерн

10. **Для множественных элементов используй count() и nth()** - не полагайся на индексацию через CSS nth-child

---

### Частые ошибки и как их избежать

❌ **НЕ делай так:**
```javascript
// Забыл await
page.getByRole('button').click();  // Не сработает!

// Использование старых селекторов без причины
page.locator('button').click();  // Лучше getByRole

// Фиксированная задержка
await page.waitForTimeout(3000);  // Антипаттерн!

// Не проверил существование
const text = await page.locator('.missing').textContent();  // Может упасть
```

✅ **Делай так:**
```javascript
// Всегда await
await page.getByRole('button', { name: 'Submit' }).click();

// Современные локаторы
await page.getByRole('button', { name: 'Submit' }).click();

// Умное ожидание
await page.waitForLoadState('networkidle');

// Проверка существования
const locator = page.locator('.optional');
if (await locator.count() > 0) {
  const text = await locator.textContent();
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
  const items = page.locator('.product-card');
  const count = await items.count();

  const products = [];
  for (let i = 0; i < Math.min(count, 10); i++) {  // Ограничить 10 элементами
    const item = items.nth(i);
    const title = await item.locator('h3').textContent();
    const price = await item.locator('.price').textContent();
    products.push({ title: title.trim(), price: price.trim() });
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

Используй эти паттерны как основу для всех операций с браузером!
"""
