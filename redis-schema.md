# MediGuard AI - Redis Caching Schema

## Purpose

Redis serves as the real-time layer for MediGuard AI, caching the **latest vitals** per patient so dashboards and alerting engines can read sub-millisecond data without hitting PostgreSQL.

---

## Key Design

### 1. Latest Vitals per Patient (Hash)

**Key pattern:** `vitals:latest:{patient_id}`

```
HSET vitals:latest:550e8400-e29b-41d4-a716-446655440000
    heart_rate       72
    systolic_bp      120
    diastolic_bp     80
    spo2             98.5
    temperature      36.8
    respiratory_rate 16
    recorded_at      "2026-05-30T14:23:01Z"
    source           "sensor"
```

**TTL:** 300 seconds (5 minutes) — auto-expires if sensor stops reporting, signaling a potential disconnect alert.

**Why a Hash?** Allows reading individual fields (`HGET`) or the full snapshot (`HGETALL`) without deserializing JSON.

---

### 2. Patient Alert Status (String with TTL)

**Key pattern:** `alert:active:{patient_id}`

```
SET alert:active:550e8400-e29b-41d4-a716-446655440000
    '{"id":"...","severity":"critical","title":"Heart rate spike","triggered_at":"2026-05-30T14:23:01Z"}'
    EX 3600
```

**TTL:** 3600 seconds (1 hour) — auto-clears if not refreshed, prevents stale alerts in cache.

---

### 3. Real-Time Vitals Stream (Redis Stream)

**Key pattern:** `stream:vitals:{patient_id}`

```
XADD stream:vitals:550e8400-e29b-41d4-a716-446655440000 *
    heart_rate 72
    systolic_bp 120
    diastolic_bp 80
    spo2 98.5
    temperature 36.8
    respiratory_rate 16
```

**Max length:** `MAXLEN ~ 1000` (approximate trimming, keeps last ~1000 readings for short-term replay).

**Consumer groups:** Alerting engine and dashboard WebSocket service each consume independently.

---

### 4. Connected Patients Set (for monitoring)

**Key pattern:** `patients:connected`

```
SADD patients:connected 550e8400-e29b-41d4-a716-446655440000
```

Remove on disconnect or TTL expiry detection. Used by the monitoring dashboard to show active patient count.

---

## Write Flow (on each vitals reading)

```python
pipe = redis.pipeline()

# 1. Update latest snapshot
pipe.hset(f"vitals:latest:{patient_id}", mapping={
    "heart_rate": reading.heart_rate,
    "systolic_bp": reading.systolic_bp,
    "diastolic_bp": reading.diastolic_bp,
    "spo2": reading.spo2,
    "temperature": reading.temperature,
    "respiratory_rate": reading.respiratory_rate,
    "recorded_at": reading.timestamp.isoformat(),
    "source": reading.source,
})
pipe.expire(f"vitals:latest:{patient_id}", 300)

# 2. Append to stream
pipe.xadd(f"stream:vitals:{patient_id}", {
    "heart_rate": reading.heart_rate,
    "systolic_bp": reading.systolic_bp,
    "diastolic_bp": reading.diastolic_bp,
    "spo2": reading.spo2,
    "temperature": reading.temperature,
    "respiratory_rate": reading.respiratory_rate,
}, maxlen=1000, approximate=True)

# 3. Mark patient as connected
pipe.sadd("patients:connected", patient_id)

pipe.execute()
```

---

## Read Patterns

| Use Case | Command | Complexity |
|----------|---------|------------|
| Dashboard: current vitals | `HGETALL vitals:latest:{pid}` | O(n) n=fields |
| Dashboard: single metric | `HGET vitals:latest:{pid} heart_rate` | O(1) |
| Alert banner | `GET alert:active:{pid}` | O(1) |
| Live chart (last 100) | `XREVRANGE stream:vitals:{pid} + - COUNT 100` | O(100) |
| Active patient count | `SCARD patients:connected` | O(1) |

---

## Eviction & Memory Strategy

- Use `volatile-ttl` eviction policy — evicts keys with shortest TTL first.
- All keys have explicit TTLs to prevent unbounded growth.
- Stream trimming (`MAXLEN ~1000`) caps per-patient memory usage.
- Estimated memory per patient: ~5 KB (hash + stream buffer).
