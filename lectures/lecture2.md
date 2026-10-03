# Лекція 2. Протоколи IIoT та edge-шлюзи

**Лабораторна: edge-шлюз з MQTT, LWT і буфером**

## Мета
Зрозуміти, які протоколи використовуються на яких рівнях, і спроєктувати шлюз, що публікує дані в MQTT надійно.

## 1. Карта протоколів

| Рівень | Протоколи | Примітка |
|---|---|---|
| Польовий | Modbus RTU/TCP, PROFIBUS, PROFINET, HART, IO-Link | «сирі» регістри |
| Контроль | OPC UA (client/server) | типізована інформаційна модель |
| Транспорт «вгору» | MQTT, AMQP, OPC UA PubSub, HTTP/REST | MQTT — де-факто стандарт для телеметрії |
| Бездротові | LoRaWAN, NB-IoT, Zigbee, 4G/5G | залежить від потужності й дальності |

Шлюз виконує **трансляцію**: Modbus/OPC UA знизу → MQTT вгору (див. курс «Програмування промислових інтерфейсів»).

## 2. MQTT: що треба знати проєктувальнику

- **Publish/Subscribe** через брокер; клієнти не знають один одного.
- **Топіки** — ієрархічні рядки: `plant/kyiv/line1/pump-01/telemetry`. Підстановки: `+` — один рівень, `#` — решта.
- **QoS**: 0 — «максимум раз» (може загубитися); 1 — «щонайменше раз» (можливі дублікати); 2 — «рівно раз» (дорожче). Для телеметрії — зазвичай 1, споживач має бути **ідемпотентним**.
- **Retained** — брокер зберігає останнє значення топіка; зручно для статусів.
- **Last Will and Testament (LWT)** — повідомлення, яке брокер публікує, якщо клієнт зник без `DISCONNECT`. Разом із retained дає надійний статус «online/offline».
- **Keepalive** — інтервал пінгів; брокер вважає клієнта мертвим після ~1,5×keepalive.
- **MQTT 5**: коди причин, `session expiry`, shared subscriptions (`$share/група/топік`) — горизонтальне масштабування споживачів.

### Проєктування простору топіків
Правила: від загального до конкретного; ідентифікатор пристрою — окремий рівень (для ACL); тип повідомлення — останній рівень; без пробілів і персональних даних; не вкладати дані у топік.

```
plant/{site}/{line}/{device}/telemetry   # потік вимірювань
plant/{site}/{line}/{device}/status      # online/offline (retained + LWT)
plant/{site}/{line}/{device}/alerts      # події
plant/{site}/{line}/{device}/cmd         # команди (окремий ACL!)
```

### Sparkplug B (стисло)
Специфікація Eclipse поверх MQTT: **фіксований простір імен** `spBv1.0/{group}/{тип}/{edge_node}/{device}`, типи `NBIRTH/NDEATH/DBIRTH/DDATA/NCMD/DCMD`, payload — Protobuf, обов'язкові «birth»-повідомлення з описом усіх метрик. Плюс: SCADA/MES бачать пристрої без індивідуальної конфігурації. Мінус: складніше, ніж «власний JSON». У курсі використовуємо простий JSON, але в реальних проєктах Sparkplug варто розглядати першим.

### OPC UA PubSub (стисло)
Частина 14 стандарту OPC UA: публікація наборів даних (DataSet) без прямого з'єднання клієнт-сервер; транспорт — UDP (UADP) або MQTT (JSON/UADP). Підходить, коли інформаційна модель уже в OPC UA.

## 3. Приклад: публікація і підписка (paho-mqtt 2.x)

```python
import json, time
import paho.mqtt.client as mqtt

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="gw-pump-01")
c.will_set("plant/kyiv/line1/pump-01/status",
           json.dumps({"state": "offline"}), qos=1, retain=True)

def on_connect(client, userdata, flags, reason_code, properties):
    client.publish("plant/kyiv/line1/pump-01/status",
                   json.dumps({"state": "online"}), qos=1, retain=True)

c.on_connect = on_connect
c.connect("localhost", 1883, keepalive=30)
c.loop_start()
c.publish("plant/kyiv/line1/pump-01/telemetry",
          json.dumps({"device_id": "pump-01", "ts": time.time(), "metrics": {"vibration_mm_s": 1.8}}),
          qos=1)
time.sleep(1); c.loop_stop()
```

Підписка:

```python
def on_message(client, userdata, msg):
    print(msg.topic, json.loads(msg.payload))

sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="viewer")
sub.on_message = on_message
sub.connect("localhost")
sub.subscribe("plant/+/+/+/telemetry", qos=1)
sub.loop_forever()
```

Запуск брокера для лабораторних: `mosquitto -c mosquitto.conf` або Docker: `docker run -p 1883:1883 eclipse-mosquitto:2` (для Mosquitto 2 потрібен конфіг із `listener 1883` та `allow_anonymous true` у навчальному режимі).

## 4. Edge-шлюз: що він має вміти

1. **Збір і нормалізація**: різні джерела → єдиний контракт даних.
2. **Буферизація** при втраті зв'язку (store-and-forward): кільцевий буфер у пам'яті або черга на диску. Політика переповнення — *відкидати найстаріше* й рахувати втрати (метрика `dropped`).
3. **Автоматичний reconnect** з експоненційною затримкою та джитером (лекція 6).
4. **Статус пристрою** (LWT + retained).
5. **Локальні правила** (фільтр «мертвої зони», агрегація) — зменшують трафік.
6. **Спостережуваність**: власні метрики шлюзу (довжина буфера, лічильник публікацій).

Шаблон «тонкого» шлюзу, що легко тестується: клас приймає *клієнта* ззовні (dependency injection) — у тестах підставляємо підроблений клієнт без мережі.

```python
class Gateway:
    def __init__(self, client, ...): ...
    def publish(self, msg):
        if self.connected: self.client.publish(...)
        else: self.buffer.push(...)
```

## 5. Типові помилки
- Публікація без LWT: «зависле» online у дашборді.
- Нескінченний буфер у пам'яті → OOM шлюзу.
- Час на пристрої без синхронізації (NTP/PTP) → «дані з майбутнього».
- Топіки з даними всередині (`.../pump-01/temp/55.2`).
- Один клієнт із тим самим `client_id` двічі — брокер відключає попереднього.

## Контрольні питання
1. У чому різниця між QoS 1 і QoS 2 і що з цього обирати для телеметрії?
2. Як LWT + retained дають надійний статус?
3. Чому для ACL зручно мати `device` окремим рівнем топіка?
4. Яку політику переповнення буфера обрати і чому?
5. Що дає Sparkplug B порівняно з довільним JSON?
