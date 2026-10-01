# Лабораторна 3. Збереження телеметрії: SQLite, агрегація, retention

**Тривалість: 2 академічні години · Лекція 3 · Файл: `iiot/storage.py`**

## Мета
Побудувати конвеєр «MQTT → база» із пакетним записом, хвилинною агрегацією та очищенням старих даних.

## Завдання
У `iiot/storage.py` реалізуйте (довга схема, див. лекцію 3):

1. `init_db(path=":memory:") -> sqlite3.Connection` — створює таблиці та індекс:
   - `telemetry(ts REAL, device_id TEXT, metric TEXT, value REAL)` + індекс `(device_id, metric, ts)`;
   - `telemetry_1m(bucket INTEGER, device_id TEXT, metric TEXT, avg REAL, min REAL, max REAL, n INTEGER, PRIMARY KEY(bucket, device_id, metric))`.
   - З'єднання має працювати з різних потоків (`check_same_thread=False`) — callback paho виконується в іншому потоці.
2. `insert_batch(conn, msgs) -> int` — одна транзакція; повертає кількість доданих **рядків** (повідомлення × метрики).
3. `last_n(conn, device_id, metric, n) -> list[(ts, value)]` — останні `n` значень у **зростаючому** порядку часу.
4. `downsample_1m(conn, before_ts)` — агрегує сирі дані з `ts < before_ts` у хвилинні відра (`bucket` = початок хвилини). **Повторний виклик не має створювати дублікатів.** Повертає кількість рядків у `telemetry_1m`.
5. `purge_older_than(conn, ts) -> int` — видаляє сирі дані з `ts < ts`, повертає кількість видалених рядків.
6. `Ingestor(conn, decoder, batch_size=20)` — `on_message(client, userdata, message)` декодує `decoder(message.payload, message.topic)`, додає в пачку; помилкові повідомлення **пропускає**, не зупиняючи роботу; при досягненні `batch_size` викликає `flush()`; `flush()` повертає кількість записаних рядків (0, якщо пачка порожня).

## Запуск
Напишіть `run_ingest.py`: підписка на `plant/+/+/+/telemetry` (QoS 1), `Ingestor(init_db("iiot.db"), lambda raw, topic: decode(raw))`, у головному циклі `flush()` раз на секунду. Запустіть разом зі шлюзом із лаб. 2 і дайте попрацювати 2–3 хвилини.

Перевірте SQL-запитами (`sqlite3 iiot.db`):
```sql
SELECT COUNT(*) FROM telemetry;
SELECT metric, AVG(value) FROM telemetry GROUP BY metric;
```

## Розрахункове завдання
Для вашого ТЗ (кількість агрегатів — ваш варіант, не менше 20) оцініть обсяг сирих і агрегованих даних на рік; запишіть у `docs/sizing.md` з припущеннями.

## Перевірка
```bash
python -m pytest tests/test_lab3_storage.py -v
```

## Захист
1. Чому пишемо пачками? Який ризик більшої пачки?
2. Чому агрегація ідемпотентна і як це забезпечено?
3. Яка політика retention підходить вашому ТЗ?
