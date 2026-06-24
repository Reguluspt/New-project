from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"


def _truthy_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() not in {"0", "false", "no", "off", "disable", "disabled"}


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, TypeError, ValueError):
        return None


def _is_pid_running(pid: int | None, command_hint: str | None = None) -> bool:
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        if not command_hint:
            return True
        try:
            cmdline_path = Path(f"/proc/{int(pid)}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text(encoding="utf-8", errors="replace").replace("\x00", " ")
                return command_hint.casefold() in cmdline.casefold()
        except Exception:
            pass
        return False

    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\").CommandLine",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except Exception:
        return False
    if not output:
        return False
    return command_hint.casefold() in output.casefold() if command_hint else True


def _find_running_pid_by_hint(command_hint: str) -> int | None:
    if os.name != "nt":
        try:
            for proc_dir in Path("/proc").glob("[0-9]*"):
                try:
                    pid = int(proc_dir.name)
                    cmdline_path = proc_dir / "cmdline"
                    if cmdline_path.exists():
                        cmdline = cmdline_path.read_text(encoding="utf-8", errors="replace").replace("\x00", " ")
                        try:
                            proc_name = (proc_dir / "comm").read_text(encoding="utf-8", errors="replace").strip()
                        except Exception:
                            proc_name = ""
                        if command_hint.casefold() in cmdline.casefold() and any(x in proc_name.lower() or x in cmdline.lower() for x in ["python", "ngrok"]):
                            return pid
                except Exception:
                    continue
        except Exception:
            pass
        return None

    try:
        escaped_hint = command_hint.replace("'", "''")
        script = (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.CommandLine -like '*{escaped_hint}*' -and "
            "($_.Name -like 'python*' -or $_.Name -like 'ngrok*') }} | "
            "Select-Object -First 1 -ExpandProperty ProcessId"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except Exception:
        return None
    try:
        return int(output.splitlines()[0])
    except (IndexError, ValueError):
        return None


def _start_hidden_process(
    args: list[str],
    *,
    pid_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    command_hint: str,
) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    existing_pid = _read_pid(pid_path)
    if _is_pid_running(existing_pid, command_hint):
        return int(existing_pid)
    discovered_pid = _find_running_pid_by_hint(command_hint)
    if discovered_pid:
        pid_path.write_text(str(discovered_pid), encoding="utf-8")
        return int(discovered_pid)

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    stdout = stdout_path.open("a", encoding="utf-8")
    stderr = stderr_path.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            args,
            cwd=str(PROJECT_ROOT),
            stdout=stdout,
            stderr=stderr,
            creationflags=creationflags,
            env=os.environ.copy(),
        )
    finally:
        stdout.close()
        stderr.close()
    pid_path.write_text(str(process.pid), encoding="utf-8")
    return int(process.pid)


def _ngrok_url_from_env() -> str:
    explicit_url = os.getenv("NGROK_URL", "").strip()
    if explicit_url:
        return explicit_url
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url:
        return ""
    parsed = urlparse(webhook_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _ngrok_public_url_online(endpoint_url: str) -> bool:
    if not endpoint_url:
        return False
    for port in ("4040", "4041", "4042"):
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/tunnels", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        for tunnel in payload.get("tunnels", []):
            if str(tunnel.get("public_url", "")).rstrip("/") == endpoint_url.rstrip("/"):
                return True
    return False


def ngrok_args() -> list[str]:
    executable = os.getenv("NGROK_PATH", "ngrok").strip() or "ngrok"
    port = os.getenv("NGROK_FORWARD_PORT", os.getenv("TELEGRAM_WEBHOOK_PORT", os.getenv("PORT", "8000"))).strip()
    target = os.getenv("NGROK_FORWARD_TARGET", port).strip() or "8000"
    endpoint_url = _ngrok_url_from_env()
    args = [executable, "http", target]
    if endpoint_url:
        args.extend(["--url", endpoint_url])
    return args


def start_ngrok_if_enabled() -> int | None:
    endpoint_url = _ngrok_url_from_env()
    # Tự động tắt ngrok nếu đã có tên miền HTTPS thực tế (không phải localhost/127.0.0.1)
    if endpoint_url and not any(x in endpoint_url.lower() for x in ["localhost", "127.0.0.1"]):
        return None

    if not _truthy_env("AUTO_START_NGROK", True):
        return None
    if _ngrok_public_url_online(endpoint_url):
        discovered_pid = _find_running_pid_by_hint("ngrok")
        if discovered_pid:
            (DATA_DIR / "ngrok.pid").write_text(str(discovered_pid), encoding="utf-8")
            return discovered_pid
    command_hint = urlparse(endpoint_url).netloc if endpoint_url else "ngrok"
    return _start_hidden_process(
        ngrok_args(),
        pid_path=DATA_DIR / "ngrok.pid",
        stdout_path=LOG_DIR / "ngrok_stdout.log",
        stderr_path=LOG_DIR / "ngrok_stderr.log",
        command_hint=command_hint,
    )


def start_telegram_webhook_if_enabled() -> int | None:
    if not _truthy_env("AUTO_START_TELEGRAM_WEBHOOK", True):
        return None
    port = os.getenv("TELEGRAM_WEBHOOK_PORT", os.getenv("PORT", "8000"))
    return _start_hidden_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.telegram_server:app",
            "--host",
            os.getenv("TELEGRAM_WEBHOOK_HOST", "0.0.0.0"),
            "--port",
            str(port),
        ],
        pid_path=PROJECT_ROOT / "telegram.pid",
        stdout_path=PROJECT_ROOT / "telegram_stdout.log",
        stderr_path=PROJECT_ROOT / "telegram_stderr.log",
        command_hint="src.telegram_server:app",
    )


def start_mail_listener_if_enabled() -> int | None:
    if not _truthy_env("AUTO_START_MAIL_LISTENER", True):
        return None
    return _start_hidden_process(
        [sys.executable, "-m", "src.mail_listener"],
        pid_path=DATA_DIR / "mail_listener.pid",
        stdout_path=LOG_DIR / "mail_listener_stdout.log",
        stderr_path=LOG_DIR / "mail_listener_stderr.log",
        command_hint="src.mail_listener",
    )


def start_flask_if_enabled() -> int | None:
    if not _truthy_env("AUTO_START_FLASK", True):
        return None
    port = os.getenv("FLASK_PORT", "5000")
    return _start_hidden_process(
        [
            sys.executable,
            "-m",
            "api.run",
            "--port",
            str(port),
        ],
        pid_path=PROJECT_ROOT / "flask.pid",
        stdout_path=PROJECT_ROOT / "flask_stdout.log",
        stderr_path=PROJECT_ROOT / "flask_stderr.log",
        command_hint="api.run",
    )


def ensure_background_services() -> dict[str, int | None]:
    if not _truthy_env("AUTO_START_BACKGROUND_SERVICES", True):
        return {"telegram": None, "mail_listener": None, "ngrok": None, "flask": None}
    return {
        "telegram": start_telegram_webhook_if_enabled(),
        "mail_listener": start_mail_listener_if_enabled(),
        "ngrok": start_ngrok_if_enabled(),
        "flask": start_flask_if_enabled(),
    }
