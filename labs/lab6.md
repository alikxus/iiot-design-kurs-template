# Лабораторна 6. Безпека: автентифікація, ACL, підпис, reconnect

**Лекція 6 · Файл: `iiot/security.py`**

## Мета
Закрити основні загрози з моделі STRIDE для вашого конвеєра.

## Частина A. Код (`iiot/security.py`)
1. Винятки: `SecurityError` та її нащадки `InvalidSignature`, `ExpiredError`, `ReplayError`.
2. `sign(secret: bytes, topic, payload: dict, ts=None, nonce=None) -> bytes` — JSON-конверт:
   ```json
   {"payload": {...}, "ts": 1760000000.0, "nonce": "a1b2...", "sig": "<hex>"}
   ```
   `sig = HMAC-SHA256(secret, f"{topic}\n{ts}\n{nonce}\n{canonical_json(payload)}")`, де `canonical_json` — `json.dumps(sort_keys=True, separators=(",", ":"))`. `ts` за замовчуванням — `time.time()`, `nonce` — випадковий (`os.urandom(8).hex()`).
3. `NonceCache(ttl=60)`: `check_and_add(nonce, now) -> bool` (False, якщо nonce уже бачили в межах TTL; застарілі записи видаляються).
4. `verify(secret, topic, raw, max_age=30, cache=None, now=None) -> dict`:
   - некоректний JSON/структура або підпис не збігся → `InvalidSignature` (порівняння `hmac.compare_digest`);
   - `|now − ts| > max_age` → `ExpiredError`;
   - nonce повторюється (якщо передано `cache`) → `ReplayError`;
   - повертає `payload`.
5. `backoff_delays(base=1.0, factor=2.0, cap=60.0, jitter=0.0, rng=None)` — нескінченний генератор: `base, base·factor, …` до `cap`; при `jitter>0` кожне значення множиться на `1 + uniform(−jitter, +jitter)`.
6. `generate_acl(devices, ingest_user="ingest", alert_user="alerts") -> str` — текст ACL Mosquitto: для кожного пристрою `user X` / `topic write plant/+/+/X/#`; `ingest` — `topic read plant/#`; `alerts` — читання телеметрії та запис у `alerts`.

## Частина B. Налаштування брокера
1. Створіть файл паролів: `mosquitto_passwd -c -b passwd pump-01 <пароль>` (повторіть для `pump-02`, `ingest`, `alerts`).
2. `python -c "from iiot.security import generate_acl; print(generate_acl(['pump-01','pump-02']))" > acl`.
3. Конфіг брокера:
   ```
   listener 1883
   allow_anonymous false
   password_file passwd
   acl_file acl
   ```
4. **Перевірте на практиці** (і занесіть у звіт): (а) підключення з неправильним паролем відхиляється; (б) `pump-01` не може публікувати в топік `pump-02` (публікація мовчки відкидається); (в) повторне відправлення перехопленого підписаного повідомлення відхиляється через `ReplayError`.

> Паролі та ключі підпису **не комітьте** в репозиторій (`.gitignore` уже виключає `passwd`, `.env`).

## Частина C. Підключення до конвеєра
Додайте підпис у шлюз (`sign`) і перевірку в ingest/alerts (`verify` із `NonceCache`). Додайте reconnect із `backoff_delays` для стартового підключення.

## Перевірка
```bash
python -m pytest tests/test_lab6_security.py -v
```

## Захист
1. Яку загрозу закриває ACL, а яку — підпис? Чому потрібні обидва?
2. Чому топік входить у підпис?
3. Які обмеження HMAC із спільним секретом?
