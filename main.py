from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.database_manager import get_db_path, log_records_db_path
from src.mail_listener import listen_forever, load_mail_listener_settings, write_listener_pid
from src.background_services import start_ngrok_if_enabled


PROJECT_ROOT = Path(__file__).resolve().parent


def load_shared_env() -> None:
    load_dotenv(PROJECT_ROOT / "API.env")
    load_dotenv(PROJECT_ROOT / ".env")
    os.environ["RECORDS_DB_PATH"] = get_db_path()
    # Đảm bảo subprocess cũng dùng UTF-8
    os.environ["PYTHONIOENCODING"] = "utf-8"


async def run_subprocess(name: str, args: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ.copy(), "PYTHONIOENCODING": "utf-8"},
    )
    print(f"[{name}] started pid={process.pid}", flush=True)
    try:
        assert process.stdout is not None
        async for raw_line in process.stdout:
            line_text = raw_line.decode("utf-8", errors="replace").rstrip()
            try:
                print(f"[{name}] {line_text}", flush=True)
            except UnicodeEncodeError:
                print(f"[{name}] {line_text.encode('ascii', errors='replace').decode()}", flush=True)
        return_code = await process.wait()
        if return_code != 0:
            raise RuntimeError(f"{name} stopped with exit code {return_code}")
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


async def run_streamlit() -> None:
    port = os.getenv("STREAMLIT_PORT", "8501")
    await run_subprocess(
        "streamlit",
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(PROJECT_ROOT / "app.py"),
            "--server.port",
            port,
            "--server.address",
            os.getenv("STREAMLIT_ADDRESS", "0.0.0.0"),
        ],
    )


async def run_telegram_webhook() -> None:
    port = os.getenv("TELEGRAM_WEBHOOK_PORT", os.getenv("PORT", "8000"))
    await run_subprocess(
        "telegram",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.telegram_server:app",
            "--host",
            os.getenv("TELEGRAM_WEBHOOK_HOST", "0.0.0.0"),
            "--port",
            port,
        ],
    )


async def run_mail_listener() -> None:
    write_listener_pid()
    settings = load_mail_listener_settings()
    interval = int(os.getenv("MAIL_LISTENER_POLL_SECONDS", "60"))
    await listen_forever(settings, poll_interval_seconds=interval)


async def main() -> None:
    load_shared_env()
    log_records_db_path("main", os.environ["RECORDS_DB_PATH"])
    tasks = [
        asyncio.create_task(run_streamlit(), name="streamlit"),
        asyncio.create_task(run_telegram_webhook(), name="telegram"),
        asyncio.create_task(run_mail_listener(), name="mail_listener"),
    ]
    start_ngrok_if_enabled()

    stop_event = asyncio.Event()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass
        done, pending = await asyncio.wait(
            [*tasks, asyncio.create_task(stop_event.wait(), name="stop_signal")],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            if task.get_name() != "stop_signal":
                task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
