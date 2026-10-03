# Лабораторна 2. Edge-шлюз: MQTT, LWT, буферизація

**Лекція 2 · Файл: `iiot/gateway.py`**

## Мета
Реалізувати шлюз, що публікує телеметрію симулятора в MQTT і не втрачає дані при розриві зв'язку.

## Підготовка
Встановіть залежності `pip install -r requirements.txt` і запустіть брокер.

`mosquitto.conf` для навчання:
```
listener 1883
allow_anonymous true
```
`mosquitto -c mosquitto.conf` або `docker run --rm -p 1883:1883 -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf" eclipse-mosquitto:2`

Спостерігати за топіками зручно через MQTT Explorer або будь-яким клієнтом із підпискою на `plant/#`.

## Завдання
У `iiot/gateway.py` реалізуйте:

1. `build_topic(site, line, device, kind="telemetry") -> str` → `plant/{site}/{line}/{device}/{kind}`.
2. `encode(msg) -> bytes` та `decode(raw) -> dict` — компактний JSON (`separators=(",", ":")`, `sort_keys=True`).
3. `OfflineBuffer(maxlen)` — кільцевий буфер: `push(item)`, `drain() -> list` (повертає й очищає, у порядку надходження), `len()`, лічильник `dropped` (скільки найстаріших відкинуто при переповненні).
4. `Gateway(client, site, line, device_id, buffer_size=1000)`:
   - у конструкторі викликає `client.will_set(<status-топік>, encode({"state":"offline"}), qos=1, retain=True)`;
   - `on_connect(*args, **kw)` — `connected=True`, публікує `{"state":"online"}` у status (qos=1, retain=True), потім скидає буфер у телеметрію **в порядку надходження**;
   - `on_disconnect(*args, **kw)` — `connected=False`;
   - `publish(msg)` — приймає `dict` або готові `bytes`; якщо підключено — `client.publish(topic, payload, qos=1)`, інакше — у буфер.
5. `make_client(client_id, username=None, password=None)` — створює `paho.mqtt.client.Client(CallbackAPIVersion.VERSION2, client_id=...)`.

Клієнт передається ззовні (*dependency injection*) — тому шлюз тестується без мережі.

## Запуск (скрипт `run_gateway.py` — напишіть самі)
Створіть клієнта, прив'яжіть `on_connect/on_disconnect`, підключіться, `loop_start()`, у циклі `sim.step()` → `gw.publish(msg)` → `sleep(1)`. Перевірте, що в `plant/#` з'являються телеметрія та `status`.

**Експеримент**: зупиніть брокер на 20 с, потім запустіть — переконайтеся, що пропущені повідомлення надійшли після відновлення (з урахуванням `dropped`).

## Перевірка
```bash
python -m pytest tests/test_lab2_gateway.py -v
```
Інтеграційний тест виконається автоматично, якщо брокер слухає `localhost:1883`.

## Захист
1. Що станеться зі статусом при аварійному вимкненні шлюзу?
2. Чому QoS 1, а не 0? Яка ціна?
3. Яку політику переповнення ви обрали і чому?
