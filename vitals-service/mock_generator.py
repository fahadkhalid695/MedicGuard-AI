"""
MediGuard AI — Mock Vitals Data Generator

Simulates 10 patients sending vitals every 2 seconds.
Occasionally injects anomalous readings to test alerting:
  - SpO2 drops to 85%
  - Heart rate spikes to 180+ bpm
  - Temperature fever spikes
  - Blood pressure crises

Usage:
    pip install httpx
    python mock_generator.py

    # Or with a custom endpoint:
    python mock_generator.py --url http://localhost:8000/api/vitals --interval 2
"""

import argparse
import asyncio
import random
import uuid
from datetime import datetime, timezone

import httpx

# 10 simulated patients with fixed UUIDs (must exist in the patients table)
PATIENTS = [
    uuid.UUID("00000000-0000-0000-0000-000000000001"),
    uuid.UUID("00000000-0000-0000-0000-000000000002"),
    uuid.UUID("00000000-0000-0000-0000-000000000003"),
    uuid.UUID("00000000-0000-0000-0000-000000000004"),
    uuid.UUID("00000000-0000-0000-0000-000000000005"),
    uuid.UUID("00000000-0000-0000-0000-000000000006"),
    uuid.UUID("00000000-0000-0000-0000-000000000007"),
    uuid.UUID("00000000-0000-0000-0000-000000000008"),
    uuid.UUID("00000000-0000-0000-0000-000000000009"),
    uuid.UUID("00000000-0000-0000-0000-000000000010"),
]

# Baseline vitals per patient (slight individual variation)
BASELINES = {
    pid: {
        "heart_rate": random.randint(65, 80),
        "bp_systolic": random.randint(110, 130),
        "bp_diastolic": random.randint(70, 85),
        "spo2": random.uniform(96.0, 99.0),
        "temperature": random.uniform(36.4, 37.0),
    }
    for pid in PATIENTS
}

# Anomaly probability per reading
ANOMALY_CHANCE = 0.08  # 8% chance of anomaly per reading


def generate_normal_reading(patient_id: uuid.UUID) -> dict:
    """Generate a realistic vitals reading with small random variation."""
    base = BASELINES[patient_id]
    return {
        "patient_id": str(patient_id),
        "heart_rate": max(40, min(180, base["heart_rate"] + random.randint(-5, 5))),
        "bp_systolic": max(80, min(200, base["bp_systolic"] + random.randint(-8, 8))),
        "bp_diastolic": max(50, min(120, base["bp_diastolic"] + random.randint(-5, 5))),
        "spo2": round(max(90.0, min(100.0, base["spo2"] + random.uniform(-1.0, 0.5))), 1),
        "temperature": round(max(35.5, min(38.0, base["temperature"] + random.uniform(-0.2, 0.2))), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def inject_anomaly(reading: dict) -> dict:
    """Inject a clinically significant anomaly into a reading."""
    anomaly_type = random.choice([
        "spo2_drop",
        "tachycardia",
        "bradycardia",
        "hypertensive_crisis",
        "fever",
        "hypothermia",
    ])

    match anomaly_type:
        case "spo2_drop":
            reading["spo2"] = round(random.uniform(82.0, 88.0), 1)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: SpO2 dropped to {reading['spo2']}%")
        case "tachycardia":
            reading["heart_rate"] = random.randint(150, 200)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: Heart rate spiked to {reading['heart_rate']} bpm")
        case "bradycardia":
            reading["heart_rate"] = random.randint(30, 45)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: Heart rate dropped to {reading['heart_rate']} bpm")
        case "hypertensive_crisis":
            reading["bp_systolic"] = random.randint(180, 240)
            reading["bp_diastolic"] = random.randint(110, 140)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: BP crisis {reading['bp_systolic']}/{reading['bp_diastolic']}")
        case "fever":
            reading["temperature"] = round(random.uniform(39.0, 41.0), 1)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: Fever at {reading['temperature']}°C")
        case "hypothermia":
            reading["temperature"] = round(random.uniform(33.0, 35.0), 1)
            print(f"  ⚠ ANOMALY [{reading['patient_id'][:8]}]: Hypothermia at {reading['temperature']}°C")

    return reading


async def send_reading(client: httpx.AsyncClient, url: str, reading: dict) -> bool:
    """Send a single vitals reading to the API."""
    try:
        response = await client.post(url, json=reading, timeout=5.0)
        if response.status_code == 201:
            return True
        else:
            print(f"  ✗ Error {response.status_code}: {response.text[:100]}")
            return False
    except httpx.RequestError as e:
        print(f"  ✗ Connection error: {e}")
        return False


async def run_generator(url: str, interval: float):
    """Main loop: generate and send vitals for all patients."""
    print("=" * 60)
    print("MediGuard AI — Mock Vitals Generator")
    print("=" * 60)
    print(f"Endpoint: {url}")
    print(f"Patients: {len(PATIENTS)}")
    print(f"Interval: {interval}s per cycle")
    print(f"Anomaly rate: {ANOMALY_CHANCE * 100:.0f}%")
    print()
    print("Patient IDs:")
    for i, pid in enumerate(PATIENTS):
        print(f"  Patient {i + 1}: {pid}")
    print()
    print("Streaming vitals... (Ctrl+C to stop)")
    print("-" * 60)

    cycle = 0
    success_count = 0
    error_count = 0

    async with httpx.AsyncClient() as client:
        try:
            while True:
                cycle += 1
                tasks = []

                for patient_id in PATIENTS:
                    reading = generate_normal_reading(patient_id)

                    # Randomly inject anomalies
                    if random.random() < ANOMALY_CHANCE:
                        reading = inject_anomaly(reading)

                    tasks.append(send_reading(client, url, reading))

                results = await asyncio.gather(*tasks)
                successes = sum(results)
                errors = len(results) - successes
                success_count += successes
                error_count += errors

                print(
                    f"[Cycle {cycle:04d}] "
                    f"Sent: {successes}/{len(PATIENTS)} | "
                    f"Total: {success_count} ok, {error_count} errors | "
                    f"{datetime.now().strftime('%H:%M:%S')}"
                )

                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print()
            print("-" * 60)
            print(f"Stopped after {cycle} cycles.")
            print(f"Total readings sent: {success_count}")
            print(f"Total errors: {error_count}")


def main():
    parser = argparse.ArgumentParser(description="MediGuard AI Mock Vitals Generator")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/vitals",
        help="Vitals ingestion endpoint URL",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between each cycle of readings",
    )
    args = parser.parse_args()

    asyncio.run(run_generator(args.url, args.interval))


if __name__ == "__main__":
    main()
