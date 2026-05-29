import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.db import get_pool
from app.models import VitalsReading, VitalsResponse
from app.redis_client import get_redis

router = APIRouter()


@router.post(
    "/vitals",
    response_model=VitalsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a real-time vitals reading",
)
async def ingest_vitals(reading: VitalsReading) -> VitalsResponse:
    """
    Accepts a vitals reading, validates ranges, persists to PostgreSQL,
    caches the latest reading in Redis, and publishes to Pub/Sub.
    """
    record_id = uuid.uuid4()

    # 1. Save to PostgreSQL
    pool = await get_pool()
    try:
        await pool.execute(
            """
            INSERT INTO vitals (id, patient_id, recorded_at, heart_rate,
                                systolic_bp, diastolic_bp, spo2, temperature)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            record_id,
            reading.patient_id,
            reading.timestamp,
            reading.heart_rate,
            reading.bp_systolic,
            reading.bp_diastolic,
            reading.spo2,
            reading.temperature,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write failed: {str(e)}",
        )

    # 2. Cache latest reading in Redis (hash with TTL)
    redis = await get_redis()
    cache_key = f"vitals:latest:{reading.patient_id}"
    cache_payload = {
        "heart_rate": str(reading.heart_rate),
        "bp_systolic": str(reading.bp_systolic),
        "bp_diastolic": str(reading.bp_diastolic),
        "spo2": str(reading.spo2),
        "temperature": str(reading.temperature),
        "timestamp": reading.timestamp.isoformat(),
    }

    cached = True
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.hset(cache_key, mapping=cache_payload)
            pipe.expire(cache_key, settings.vitals_cache_ttl)
            await pipe.execute()
    except Exception:
        cached = False  # Non-fatal: log but don't fail the request

    # 3. Publish to Redis Pub/Sub channel
    published = True
    try:
        channel = f"vitals:{reading.patient_id}"
        pub_payload = json.dumps(
            {
                "id": str(record_id),
                "patient_id": str(reading.patient_id),
                "heart_rate": reading.heart_rate,
                "bp_systolic": reading.bp_systolic,
                "bp_diastolic": reading.bp_diastolic,
                "spo2": reading.spo2,
                "temperature": reading.temperature,
                "timestamp": reading.timestamp.isoformat(),
            }
        )
        await redis.publish(channel, pub_payload)
    except Exception:
        published = False  # Non-fatal

    return VitalsResponse(
        id=record_id,
        patient_id=reading.patient_id,
        heart_rate=reading.heart_rate,
        bp_systolic=reading.bp_systolic,
        bp_diastolic=reading.bp_diastolic,
        spo2=reading.spo2,
        temperature=reading.temperature,
        timestamp=reading.timestamp,
        cached=cached,
        published=published,
    )


@router.get(
    "/vitals/{patient_id}/latest",
    summary="Get the latest cached vitals for a patient",
)
async def get_latest_vitals(patient_id: uuid.UUID):
    """Returns the latest cached vitals from Redis, or 404 if expired/missing."""
    redis = await get_redis()
    cache_key = f"vitals:latest:{patient_id}"
    data = await redis.hgetall(cache_key)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cached vitals found. Reading may have expired or patient has no recent data.",
        )

    return {
        "patient_id": str(patient_id),
        "heart_rate": int(data["heart_rate"]),
        "bp_systolic": int(data["bp_systolic"]),
        "bp_diastolic": int(data["bp_diastolic"]),
        "spo2": float(data["spo2"]),
        "temperature": float(data["temperature"]),
        "timestamp": data["timestamp"],
        "source": "cache",
    }


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "vitals-ingestion", "timestamp": datetime.utcnow().isoformat()}
