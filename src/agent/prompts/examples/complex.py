"""Сложные примеры - decision-making и error recovery patterns."""

COMPLEX_EXAMPLES = """## Продвинутые reasoning паттерны

### Паттерн: Итеративная обработка с условной логикой
Принцип: При обработке множества элементов - сначала наблюдение, затем принятие решения.

Meta-pattern:
- Определить критерии принятия решения ДО начала цикла
- Для каждого элемента: извлечь данные → оценить по критериям → действовать
- После действий которые меняют страницу - обновить данные
- Избегать принятия решений на устаревшей информации

Decision-making flow:
observe all → establish criteria → evaluate each → act based on evaluation → verify results

### Паттерн: Graceful error recovery
Принцип: Ошибки - нормальная часть работы с динамическим контентом.

Recovery strategy:
1. Обнаружение ошибки (stale refs, network timeout, element not found)
2. Анализ причины (страница изменилась? медленная сеть? элемент исчез?)
3. Выбор стратегии восстановления:
   - Stale refs → обновить данные о странице → повторить
   - Network issue → подождать → повторить
   - Element disappeared → изменить стратегию поиска
4. Ограничение попыток (3 retry max) → иначе сообщить пользователю

Anti-pattern: Бесконечные retry без изменения стратегии

### Паттерн: Multi-step decision making
Принцип: Не все задачи решаются линейно - иногда нужен сбор данных перед действием.

Когда применять "observe before act":
- Задачи со сравнением (найти лучший, самый дешевый, подходящий)
- Задачи с условной логикой (если X то Y, иначе Z)
- Задачи требующие валидации (проверить перед подтверждением)

Process:
1. Определить что нужно знать для принятия решения
2. Собрать все необходимые данные
3. Проанализировать и принять решение
4. Действовать на основе решения
5. Верифицировать результат

### Паттерн: Adaptive behavior при неожиданных состояниях
Принцип: Реальность отличается от ожиданий - нужна адаптация.

Taxonomy неожиданных состояний:
- Требует действий человека (авторизация, CAPTCHA) → уведомить и ждать
- Временная проблема (загрузка, обработка) → retry с delay
- Изменение структуры (редизайн, A/B тест) → адаптировать стратегию
- Тупик (страница недоступна, функция удалена) → сообщить и предложить альтернативы

Adaptive reasoning:
expect the expected, prepare for the unexpected, communicate clearly

### Паттерн: State Verification для action tasks
Принцип: Различай задачи на сбор информации и задачи на изменение состояния.

**Research task** (информация):
- User: "Найди цену на товар X"
- Process: navigate → extract data → return to user
- Verification: НЕ требуется (результат = извлеченные данные)
- Completion: когда данные предоставлены пользователю

**Action task** (изменение состояния):
- User: "Добавь N элементов в контейнер"
- Process: find elements → execute actions → **VERIFY state changed**
- Verification: ОБЯЗАТЕЛЬНА (результат = новое состояние системы)
- Completion: только после проверки финального состояния

Complete workflow для action task:
```
1. Task decomposition
   "Что должно измениться? Как проверю что изменилось?"

2. Execute actions
   navigate → interact → perform operations

3. State verification (КРИТИЧНО!)
   - Запомни состояние ДО (или предскажи начальное)
   - Проверь состояние ПОСЛЕ
   - Сравни: before ≠ after

4. Evidence collection
   - Конкретные факты: "counter changed from 0 to 3"
   - Визуальные доказательства: "container now shows 3 items"
   - State queries: "check returns confirmed status"

5. Completion
   Только если verification passed → задача выполнена
```

**Anti-pattern** (типичная ошибка):
```
Task: "Добавь элементы в список"
❌ WRONG:
   → find elements
   → click "add" buttons
   → assume success
   → complete ✗

✓ CORRECT:
   → find elements
   → click "add" buttons
   → verify list count increased
   → verify items visible in list
   → complete ✓
```

Key insight: Выполнение действия ≠ Достижение цели
- Клик может не сработать (modal блокирует)
- Форма может не отправиться (validation error)
- Навигация может не произойти (redirect)

**ВСЕГДА** проверяй финальное состояние для action tasks.
"""
