"""Класс запуска Camoufox с настройками и прокси."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from camoufox import DefaultAddons
from camoufox.sync_api import Camoufox
from playwright.sync_api import Browser

from browser_automation.proxy import VlessProxy
from browser_automation.value_objects import CamoufoxSettings, Profile, ProxyConfig

if TYPE_CHECKING:
    from browser_automation.proxy import ProxyBase


class CamoufoxLauncher:
    """
    Запуск Camoufox с настройками и опциональным прокси.
    В __init__ можно передать profile или отдельно proxy, settings.
    """

    def __init__(
        self,
        *,
        profile: Profile | None = None,
        proxy: "ProxyBase | ProxyConfig | None" = None,
        settings: CamoufoxSettings | None = None,
        data_dir: Path | str | None = None,
    ) -> None:
        self._profile = profile
        self._proxy = proxy
        self._settings = settings or CamoufoxSettings()
        if profile and profile.camoufox_settings:
            self._settings = profile.camoufox_settings
        self._data_dir = Path(data_dir) if data_dir else None
        self._browser: Browser | None = None
        self._proxy_process: ProxyBase | None = None
        self._proxy_config: ProxyConfig | None = None

    def start(self) -> Browser:
        """Запускает Camoufox (и прокси если задан)."""
        proxy_config: ProxyConfig | None = None

        if self._proxy is not None:
            if isinstance(self._proxy, ProxyConfig):
                proxy_config = self._proxy
            elif isinstance(self._proxy, VlessProxy):
                self._proxy_process = self._proxy
                proxy_config = self._proxy.start()
                self._proxy_config = proxy_config

        if self._profile and self._profile.vless_raw and not proxy_config:
            try:
                start_port = (
                    self._profile.proxy_config.port
                    if self._profile.proxy_config
                    else 10808
                )
                vless = VlessProxy(self._profile.vless_raw, local_port=start_port)
                self._proxy_process = vless
                proxy_config = vless.start()
                self._proxy_config = proxy_config
            except Exception:
                pass

        # headless=False — окно должно быть видимым
        kwargs: dict = {
            "headless": self._settings.headless,  # по умолчанию False
            "humanize": self._settings.humanize,
            "exclude_addons": [DefaultAddons.UBO] if self._settings.exclude_ublock else [],
        }
        if self._settings.window:
            kwargs["window"] = self._settings.window
        if self._data_dir:
            kwargs["user_data_dir"] = str(self._data_dir)
        if proxy_config:
            kwargs["proxy"] = proxy_config.to_playwright_proxy()
            kwargs["geoip"] = True  # устраняет LeakWarning, согласует гео/локаль с IP прокси

        camoufox = Camoufox(**kwargs)
        self._browser = camoufox.start()
        page = self._browser.new_page()
        page.goto("about:blank")
        # Заголовок окна = название профиля
        if self._profile and self._profile.name:
            page.evaluate(f"document.title = {json.dumps(self._profile.name)}")
        page.bring_to_front()
        return self._browser

    def is_running(self) -> bool:
        """Проверяет, подключён ли браузер (не закрыт ли вручную)."""
        if not self._browser:
            return False
        try:
            return self._browser.is_connected()
        except Exception:
            return False

    def stop(self) -> None:
        """Останавливает браузер и VLESS/xray-прокси (если был запущен)."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._proxy_process:
            self._proxy_process.stop()
            self._proxy_process = None
        self._proxy_config = None
