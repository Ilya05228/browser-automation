"""Value Objects для профилей, прокси, VLESS и др."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True)
class ProxyAddress:
    """Адрес прокси: host:port."""

    host: str
    port: int

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class VlessString:
    """
    VO для VLESS-строки. Валидирует и парсит.
    Формат: vless://uuid@host:port?params#name
    """

    def __init__(self, raw: str) -> None:
        if not raw or not raw.strip():
            raise ValueError("VLESS строка не может быть пустой")
        s = raw.strip()
        if not s.lower().startswith("vless://"):
            raise ValueError("VLESS строка должна начинаться с vless://")
        parsed = urlparse(s)
        if parsed.scheme.lower() != "vless":
            raise ValueError("Схема должна быть vless")
        netloc = parsed.netloc
        if "@" not in netloc:
            raise ValueError("VLESS: ожидается uuid@host:port")
        userinfo, hostport = netloc.rsplit("@", 1)
        uuid = userinfo
        if not uuid or len(uuid) < 20:
            raise ValueError("VLESS: uuid невалидный")
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"VLESS: порт должен быть числом: {port_str}")
        else:
            raise ValueError("VLESS: host:port обязательны")
        self._raw = s
        self._uuid = uuid
        self._host = host
        self._port = port
        self._params = parse_qs(parsed.query) if parsed.query else {}
        self._name = unquote(parsed.fragment) if parsed.fragment else ""

    @property
    def raw(self) -> str:
        return self._raw

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def name(self) -> str:
        return self._name

    def param(self, key: str, default: str = "") -> str:
        v = self._params.get(key, [default])
        return v[0] if v else default

    def to_dict(self) -> dict[str, Any]:
        return {
            "security": self.param("security", "reality"),
            "type": self.param("type", "tcp"),
            "flow": self.param("flow", ""),
            "sni": self.param("sni", self._host),
            "fp": self.param("fp", "random"),
            "pbk": self.param("pbk", ""),
            "sid": self.param("sid", ""),
            "path": self.param("path", ""),
            "host": self.param("host", ""),
        }


@dataclass
class ProxyConfig:
    """Настройки прокси для Camoufox (host, port)."""

    host: str
    port: int

    def to_proxy_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_playwright_proxy(self) -> dict:
        return {"server": f"socks5://{self.host}:{self.port}"}


# Локаль браузера (Accept-Language, locale)
DEFAULT_LOCALE = "ru-BY,ru-RU"


@dataclass
class CamoufoxSettings:
    """Настройки запуска Camoufox."""

    headless: bool = False
    humanize: bool = True
    exclude_ublock: bool = True
    window: tuple[int, int] | None = None
    enable_cache: bool = True
    locale: str = DEFAULT_LOCALE


# Версия схемы профиля (для миграций при изменении формата)
PROFILE_VERSION = 1


@dataclass
class Profile:
    """
    Профиль: название, куки, прокси, настройки Camoufox.
    cookies — список куков в формате Playwright (name, value, domain, path, ...).
    version — версия схемы профиля для миграций.
    """

    id: str
    name: str
    cookies: list[dict[str, Any]] | None = None
    proxy_config: ProxyConfig | None = None
    vless_raw: str | None = None
    camoufox_settings: CamoufoxSettings | None = None
    version: int = PROFILE_VERSION

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "id": self.id,
            "name": self.name,
            "cookies": self.cookies if self.cookies is not None else [],
        }
        if self.proxy_config:
            d["proxy"] = {
                "host": self.proxy_config.host,
                "port": self.proxy_config.port,
            }
        if self.vless_raw:
            d["vless_raw"] = self.vless_raw
        if self.camoufox_settings:
            s = self.camoufox_settings
            d["camoufox"] = {
                "headless": s.headless,
                "humanize": s.humanize,
                "exclude_ublock": s.exclude_ublock,
                "window": s.window,
                "enable_cache": s.enable_cache,
                "locale": s.locale,
            }
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Profile":
        proxy = None
        if "proxy" in d and d["proxy"]:
            proxy = ProxyConfig(
                host=d["proxy"].get("host", "127.0.0.1"),
                port=int(d["proxy"].get("port", 10808)),
            )
        camo = None
        if "camoufox" in d and d["camoufox"]:
            c = d["camoufox"]
            camo = CamoufoxSettings(
                headless=c.get("headless", False),
                humanize=c.get("humanize", True),
                exclude_ublock=c.get("exclude_ublock", True),
                window=tuple(c["window"]) if c.get("window") else None,
                enable_cache=c.get("enable_cache", True),
                locale=c.get("locale", DEFAULT_LOCALE),
            )
        raw_cookies = d.get("cookies")
        cookies: list[dict[str, Any]] | None = None
        if isinstance(raw_cookies, list):
            cookies = raw_cookies
        elif raw_cookies:
            cookies = []

        version = int(d.get("version", PROFILE_VERSION))

        return cls(
            id=d.get("id", ""),
            name=d.get("name", "Unnamed"),
            cookies=cookies,
            proxy_config=proxy,
            vless_raw=d.get("vless_raw"),
            camoufox_settings=camo,
            version=version,
        )
