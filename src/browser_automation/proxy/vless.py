"""VLESS-прокси через xray-core."""

import json
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from browser_automation.proxy.base import ProxyBase
from browser_automation.value_objects import ProxyConfig, VlessString


def find_free_port(start: int = 10808) -> int:
    """Ищет свободный порт начиная с start. Если занят — +1, +2, … пока не найдёт."""
    for port in range(start, start + 1000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Не найден свободный порт в диапазоне {start}-{start+1000}")


def _find_xray() -> str:
    """Возвращает путь к xray. Windows: xray.exe, Linux/Ubuntu: xray (из PATH)."""
    if sys.platform == "win32":
        candidates = ["xray.exe", "xray"]
    else:
        candidates = ["xray"]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    if sys.platform == "win32":
        raise FileNotFoundError(
            "xray не найден. Установите Xray-core (https://github.com/XTLS/Xray-core) "
            "и добавьте xray.exe в PATH, либо укажите путь вручную."
        )
    raise FileNotFoundError(
        "xray не найден. Установите: Ubuntu/Debian — apt install xray (или скачайте с GitHub), "
        "добавьте в PATH. Либо укажите путь вручную."
    )


class VlessProxy(ProxyBase):
    """
    Прокси на базе VLESS. Принимает VLESS-строку, запускает xray-core
    с локальным SOCKS5/HTTP inbound и VLESS outbound.
    Требует установленный xray в PATH (Windows: xray.exe, Linux: xray).
    При stop() xray завершается.
    """

    def __init__(
        self,
        vless_string: str | VlessString,
        *,
        local_port: int = 10808,
        xray_path: str | Path | None = None,
    ) -> None:
        if isinstance(vless_string, str):
            vless_string = VlessString(vless_string)
        self._vless = vless_string
        self._local_port = local_port
        self._xray_path = str(xray_path) if xray_path else _find_xray()
        self._process: subprocess.Popen | None = None
        self._config_path: Path | None = None

    def _build_xray_config(self) -> dict:
        """Генерирует конфиг xray из VLESS-строки."""
        v = self._vless
        security = v.param("security", "reality")
        net = v.param("type", "tcp")
        flow = v.param("flow", "")
        sni = v.param("sni", v.host)
        fp = v.param("fp", "random")
        pbk = v.param("pbk", "")
        sid = v.param("sid", "")
        path = v.param("path", "")
        host = v.param("host", sni) or sni

        outbound: dict = {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": v.host,
                        "port": v.port,
                        "users": [
                            dict(
                                id=v.uuid,
                                encryption="none",
                                **({"flow": flow} if flow else {}),
                            )
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": net,
                "security": security,
            },
        }

        if security == "reality" and pbk:
            outbound["streamSettings"]["realitySettings"] = {
                "serverName": sni,
                "fingerprint": fp,
                "publicKey": pbk,
                "shortId": sid or "",
                "show": False,
            }

        if net == "tcp" and host:
            outbound["streamSettings"]["tcpSettings"] = {
                "header": {"type": "none"},
            }
        elif net == "ws":
            outbound["streamSettings"]["wsSettings"] = {
                "path": path or "/",
                "headers": {"Host": host},
            }
        elif net == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {
                "serviceName": path or "grpc",
            }

        return {
            "log": {"loglevel": "warning"},
            "inbounds": [
                {
                    "port": self._local_port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {"udp": True},
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
                },
                {
                    "port": self._local_port + 1,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {},
                },
            ],
            "outbounds": [outbound],
        }

    def start(self) -> ProxyConfig:
        if self._process is not None:
            return ProxyConfig("127.0.0.1", self._local_port)

        # Ищем свободный порт: start, start+1, … пока не найдём
        self._local_port = find_free_port(max(10808, self._local_port))

        resolved = shutil.which(self._xray_path)
        if not resolved and Path(self._xray_path).exists():
            resolved = str(Path(self._xray_path).resolve())
        if not resolved:
            raise FileNotFoundError(
                f"xray не найден: {self._xray_path}. "
                "Установите Xray-core (Windows: xray.exe, Ubuntu: apt install xray) и добавьте в PATH."
            )
        self._xray_path = resolved
        config = self._build_xray_config()
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            import os

            with os.fdopen(fd, "w") as f:
                json.dump(config, f, indent=2)
            self._config_path = Path(path)
        except Exception:
            import os

            try:
                os.close(fd)
            except Exception:
                pass
            Path(path).unlink(missing_ok=True)
            raise

        self._process = subprocess.Popen(
            [self._xray_path, "run", "-c", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return ProxyConfig("127.0.0.1", self._local_port)

    def stop(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception:
            try:
                self._process.kill()
            except Exception:
                pass
        self._process = None
        if self._config_path and self._config_path.exists():
            try:
                self._config_path.unlink()
            except Exception:
                pass
        self._config_path = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
