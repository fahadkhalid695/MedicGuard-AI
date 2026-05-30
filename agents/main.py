"""
MediGuard AI — Multi-Agent Monitoring System

Runs all 4 specialist agents + the OrchestratorAgent concurrently,
each subscribing to Redis Pub/Sub vitals channels.

Usage:
    pip install -r requirements.txt
    python -m agents.main

    # Monitor specific patients:
    PATIENT_IDS="uuid1,uuid2" python -m agents.main
"""

import asyncio
import signal
import sys

from agents.cardiac_agent import CardiacAgent
from agents.config import PATIENT_IDS
from agents.orchestrator_agent import OrchestratorAgent
from agents.respiratory_agent import RespiratoryAgent
from agents.thermal_agent import ThermalAgent
from agents.trend_agent import TrendAgent


async def run_all_agents():
    """Start all monitoring agents + orchestrator concurrently."""
    print("=" * 60)
    print("  MediGuard AI — Multi-Agent Monitoring System")
    print("=" * 60)
    print()

    # Initialize specialist agents
    specialists = [
        CardiacAgent(),
        RespiratoryAgent(),
        ThermalAgent(),
        TrendAgent(),
    ]

    # Initialize orchestrator
    orchestrator = OrchestratorAgent()

    patient_ids = PATIENT_IDS if PATIENT_IDS else None
    if patient_ids:
        print(f"Monitoring {len(patient_ids)} specific patients")
    else:
        print("Monitoring ALL patients (pattern subscription)")
    print()

    # Create tasks: specialists + orchestrator
    tasks = [
        asyncio.create_task(agent.start(patient_ids), name=agent.name)
        for agent in specialists
    ]
    tasks.append(
        asyncio.create_task(orchestrator.start(patient_ids), name=orchestrator.name)
    )

    all_agents = [*specialists, orchestrator]

    # Handle graceful shutdown
    def handle_signal():
        print("\n\nShutdown signal received. Stopping agents...")
        for agent in all_agents:
            agent.stop()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)
    else:
        signal.signal(signal.SIGINT, lambda *_: handle_signal())

    print(f"All agents active ({len(specialists)} specialists + 1 orchestrator). Press Ctrl+C to stop.")
    print("-" * 60)

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("\nAll agents stopped. Goodbye.")


def main():
    try:
        asyncio.run(run_all_agents())
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
