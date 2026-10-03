# Лабораторна 4. Рушій сповіщень: поріг, гістерезис, debounce

**Лекція 4 · Файл: `iiot/alerts.py`**

## Мета
Реалізувати конфігурований рушій правил, який не «дрижить» біля порога, і підключити його до шини.

## Завдання
У `iiot/alerts.py`:

1. `@dataclass Rule(name, metric, high, hysteresis=0.0, debounce=3, severity="warning")`.
2. `AlertEngine(rules)` з методом `process(msg) -> list[dict]`:
   - стан зберігається **окремо для кожної пари (device_id, rule.name)**;
   - **raised**: після `debounce` вимірів **поспіль**, у яких `value > high`; будь-який вимір не вище порога скидає лічильник;
   - **cleared**: коли активне сповіщення і `value < high − hysteresis`;
   - подія генерується **лише при переходах**;
   - якщо метрики немає в повідомленні — правило пропускається;
   - формат події:
     ```json
     {"rule":"high_vibration","device_id":"pump-01","metric":"vibration_mm_s",
      "state":"raised","value":5.1,"ts":1760000123.4,"severity":"critical"}
     ```
3. `DEFAULT_RULES`: `high_vibration` (поріг 4,5, гістерезис 0,5, debounce 3, critical) та `high_temperature` (поріг 80, гістерезис 3, debounce 5, warning).

## Запуск
`run_alerts.py`: підписка на телеметрію; для кожної події — публікація в топік, у якого останній сегмент замінено на `alerts` (`plant/.../pump-01/alerts`), QoS 1. Викличте у симуляторі `inject_fault("bearing")` і переконайтеся, що подія `raised` з'явилась, а після `running=False`/ремонту (скид `wear`) — `cleared`.

## Перевірка
```bash
python -m pytest tests/test_lab4_alerts.py -v
```

## Додатково
Додайте правило «відсутність даних понад 30 с» (потрібен таймер, а не лише `process`) та зобразіть пороги на графіку (matplotlib) по даних із `iiot.db`.

## Захист
1. Покажіть на послідовності значень, чим debounce відрізняється від гістерезису.
2. Як зменшити кількість хибних спрацювань, не втративши реальні?
3. Які поля події потрібні оператору для дії?
