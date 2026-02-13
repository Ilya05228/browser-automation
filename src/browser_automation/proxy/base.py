"""Базовый класс прокси."""

from abc import ABC, abstractmethod

from browser_automation.value_objects import ProxyConfig


class ProxyBase(ABC):
    """Абстрактный базовый класс прокси. При запуске даёт локальный proxy_config."""

    @abstractmethod
    def start(self) -> ProxyConfig:
        """Запускает прокси, возвращает ProxyConfig (host, port)."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Останавливает прокси."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Проверяет, запущен ли прокси."""
        ...
