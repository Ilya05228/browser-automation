"""Хранилище профилей в JSON. CRUD операции."""

import json
import uuid
from pathlib import Path

from browser_automation.value_objects import PROFILE_VERSION, Profile


class ProfileRepository:
    """CRUD для профилей в JSON-файле."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict]:
        try:
            data = self._path.read_text(encoding="utf-8")
            return json.loads(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, items: list[dict]) -> None:
        self._path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_all(self) -> list[Profile]:
        """Список всех профилей."""
        items = self._load()
        return [Profile.from_dict(d) for d in items]

    def get(self, profile_id: str) -> Profile | None:
        """Получить профиль по id."""
        for p in self.list_all():
            if p.id == profile_id:
                return p
        return None

    def create(self, profile: Profile) -> Profile:
        """Создать профиль (id генерируется если пустой)."""
        items = self._load()
        p = profile
        if not p.id:
            p = Profile(
                id=str(uuid.uuid4()),
                name=p.name,
                cookies=p.cookies,
                proxy_config=p.proxy_config,
                vless_raw=p.vless_raw,
                camoufox_settings=p.camoufox_settings,
                version=getattr(p, "version", PROFILE_VERSION),
            )
        items.append(p.to_dict())
        self._save(items)
        return p

    def update(self, profile: Profile) -> Profile:
        """Обновить профиль."""
        items = self._load()
        for i, d in enumerate(items):
            if d.get("id") == profile.id:
                items[i] = profile.to_dict()
                self._save(items)
                return profile
        raise KeyError(f"Профиль не найден: {profile.id}")

    def delete(self, profile_id: str) -> bool:
        """Удалить профиль. Возвращает True если удалён."""
        items = self._load()
        new_items = [d for d in items if d.get("id") != profile_id]
        if len(new_items) == len(items):
            return False
        self._save(new_items)
        return True

    def copy(self, profile_id: str, new_name: str | None = None) -> Profile | None:
        """Копировать профиль. Возвращает новый профиль."""
        p = self.get(profile_id)
        if not p:
            return None
        copy = Profile(
            id="",
            name=new_name or f"{p.name} (копия)",
            cookies=p.cookies,
            proxy_config=p.proxy_config,
            vless_raw=p.vless_raw,
            camoufox_settings=p.camoufox_settings,
            version=getattr(p, "version", PROFILE_VERSION),
        )
        return self.create(copy)

    def export_profile(self, profile_id: str) -> dict:
        """Экспорт одного профиля в словарь."""
        p = self.get(profile_id)
        if not p:
            raise KeyError(f"Профиль не найден: {profile_id}")
        return p.to_dict()

    def import_profile(self, data: dict) -> Profile:
        """Импорт профиля из словаря. id будет новый."""
        p = Profile.from_dict(data)
        p = Profile(
            id="",
            name=p.name,
            cookies=p.cookies,
            proxy_config=p.proxy_config,
            vless_raw=p.vless_raw,
            camoufox_settings=p.camoufox_settings,
            version=getattr(p, "version", PROFILE_VERSION),
        )
        return self.create(p)
