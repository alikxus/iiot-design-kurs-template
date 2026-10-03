# Лабораторна 7. Інтеграція, Docker Compose, захист проєкту

**Лекція 7 · Файли: `iiot/config.py`, `iiot/services/*`, `deploy/*`**

## Мета
Зібрати лаб. 1–6 в єдину систему, що запускається однією командою, та підготувати проєкт до захисту.

## Завдання
1. `iiot/config.py` — клас `Config` зі змінними середовища: `MQTT_HOST` (localhost), `MQTT_PORT` (1883), `MQTT_USER`, `MQTT_PASSWORD`, `SITE` (kyiv), `LINE` (line1), `DEVICE_ID` (pump-01), `INTERVAL` (1.0), `SIGNING_KEY` (байти або `None`), `DB_PATH` (iiot.db), `FAULT_AFTER` (секунди або `None`), `HEALTH_FILE` (/tmp/healthy). Порожній рядок = «не задано».
2. Пакет `iiot/services/` (потрібен `__init__.py`) із модулями, що запускаються як `python -m iiot.services.<ім'я>`:
   - `gateway_service` — симулятор + шлюз; підписує повідомлення, якщо задано `SIGNING_KEY`; після `FAULT_AFTER` с викликає `inject_fault("bearing")`;
   - `ingest_service` — підписка на телеметрію → SQLite; перевіряє підпис, якщо задано ключ;
   - `alert_service` — правила → публікація в `.../alerts` (підписує, якщо є ключ).
   - Усі: підключення з повторними спробами (`backoff_delays`), оновлення `HEALTH_FILE` у головному циклі.
3. `deploy/Dockerfile`, `deploy/docker-compose.yml` (брокер, ≥ 2 шлюзи, ingest, alerts), `deploy/mosquitto.conf`, `deploy/make_passwd.sh`; health-check для кожного сервісу; томи для даних брокера й БД; `restart: unless-stopped`.
4. `docs/` — підсумкова документація: `tz.md` (з лаб. 1, актуалізоване), `architecture.md` (схема, топіки, контракт повідомлення), `security.md` (модель загроз і налаштування), `deploy.md` (інструкція), `tco.md` (оцінка вартості пілоту з припущеннями).

## Перевірка
```bash
# наскрізний тест (потрібен брокер на localhost:1883, без автентифікації):
python -m pytest tests/test_lab7_e2e.py -v
# повний набір:
python -m pytest -v
```
Тест запускає ваші три сервіси, вмикає несправність і чекає на підписану подію `raised` у `alerts` та ≥ 20 рядків у БД.

Запуск стека:
```bash
cd deploy
cp .env.example .env     # задайте SIGNING_KEY
./make_passwd.sh pump-01 pump-02 ingest alerts
python gen_acl.py pump-01 pump-02 > acl     # PYTHONPATH=.. 
docker compose up --build -d
docker compose ps        # усі сервіси healthy
docker compose logs -f alerts
```

## Захист проєкту (демонстрація 10–12 хв)
1. Запуск стека; статус пристроїв.
2. Потік даних і запис у БД (запит SQL).
3. Сповіщення при несправності; його зняття.
4. Безпека: невірний пароль, чужий топік, replay.
5. Відповіді на 2–3 питання за архітектурою, ТЗ і TCO.

## Критерії оцінювання (приклад)
| Складова | Бал |
|---|---|
| Усі тести лаб. 1–7 зелені | 30 |
| Docker Compose запускається за інструкцією | 20 |
| Документація (ТЗ, архітектура, безпека, TCO) | 20 |
| Демонстрація та відповіді | 20 |
| Додаткові завдання / якість коду | 10 |
