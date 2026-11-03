"""Ctrl+C during bot setup must release resources without needing a second keypress."""

import asyncio
import signal
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import main


class ShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_translation_loop_is_sequential(self) -> None:
        calls = []
        complete = asyncio.Event()

        async def fake_worker(*_args):
            calls.append(("started", asyncio.get_running_loop().time()))
            await asyncio.sleep(0.02)
            calls.append(("finished", asyncio.get_running_loop().time()))
            if len(calls) >= 4:
                complete.set()

        with (
            patch.object(main, "translation_worker", side_effect=fake_worker),
            patch.object(main.config, "TRANSLATION_WORKER_SECONDS", 0.01),
        ):
            task = asyncio.create_task(main.translation_loop(None, None))
            try:
                await asyncio.wait_for(complete.wait(), timeout=1)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertEqual([event for event, _ in calls[:4]], [
            "started", "finished", "started", "finished",
        ])
        self.assertGreaterEqual(calls[2][1] - calls[1][1], 0.01)

    async def test_sigint_during_setup_closes_database_and_session(self) -> None:
        database = MagicMock()
        database.connect = AsyncMock()
        database.close = AsyncMock()
        bot = MagicMock()
        bot.session.close = AsyncMock()
        dispatcher = MagicMock()
        dispatcher._stop_signal = None
        dispatcher._running_lock.locked.return_value = False
        router = SimpleNamespace(message=MagicMock(), callback_query=MagicMock())
        previous = signal.getsignal(signal.SIGINT)

        async def interrupt_during_setup(_bot):
            signal.raise_signal(signal.SIGINT)
            await asyncio.sleep(0.05)

        with (
            patch.object(main, "setup_logging"),
            patch.object(main, "Database", return_value=database),
            patch.object(main, "Bot", return_value=bot),
            patch.object(main, "Dispatcher", return_value=dispatcher),
            patch.object(main, "router", router),
            patch.object(main, "_configure_bot", side_effect=interrupt_during_setup),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(asyncio.create_task(main.run()), timeout=2)

        database.close.assert_awaited_once()
        bot.session.close.assert_awaited_once()
        self.assertIs(signal.getsignal(signal.SIGINT), previous)
