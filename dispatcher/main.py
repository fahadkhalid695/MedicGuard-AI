"""
MediGuard AI — AlertDispatcher Service

Consumes unified alerts from a Redis queue and routes notifications
based on severity level. Runs the WebSocket server for in-app notifications.

Usage:
    pip install -r requirements.txt
    python -m dispatcher.main
"""

import asyncio
import signal
import sys

from dispatcher.channels.websocket import ws_manager
from dispatcher.dispatcher import AlertDispatcher


async def run_dispatcher():
    """Start the dispatcher and WebSocket server."""
    print("=" * 60)
    print("  MediGuard AI — AlertDispatcher Service")
    print("=" * 60)
    print()

    dispatcher = AlertDispatcher()

    # Start WebSocket server for in-app notifications
    await ws_manager.start_server()

    # Handle graceful shutdown
    def handle_signal():
        print("\n\nShutdown signal received...")
        dispatcher.stop()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)
    else:
        signal.signal(signal.SIGINT, lambda *_: handle_signal())

    try:
        await dispatcher.start()
    finally:
        await ws_manager.stop_server()
        print("\nAlertDispatcher stopped.")


def main():
    try:
        asyncio.run(run_dispatcher())
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
