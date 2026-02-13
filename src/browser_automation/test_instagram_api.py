"""
Тест официального Instagram Content Publishing API.
Публикация Reels через Graph API (аккаунт должен быть профессиональным и привязан к странице).
Ключи и ID запрашиваются из .env.
Запуск: uv run test-api  (или python -m browser_automation.test_instagram_api)
"""

import os
import sys
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_BASE = "https://graph.instagram.com"
API_VERSION = "v21.0"


class InstagramReelsPublisher:
    """
    Публикация Reels через Instagram Content Publishing API.
    Нужны: access_token и ig_account_id (профессиональный аккаунт).
    Видео для публикации — по публичной ссылке (video_url).
    """

    def __init__(
        self,
        *,
        access_token: str,
        ig_account_id: str,
        api_version: str = API_VERSION,
    ) -> None:
        if not access_token or not access_token.strip():
            raise ValueError("INSTAGRAM_ACCESS_TOKEN не задан или пустой")
        if not ig_account_id or not ig_account_id.strip():
            raise ValueError("INSTAGRAM_ACCOUNT_ID не задан или пустой")
        self.access_token = access_token.strip()
        self.ig_account_id = ig_account_id.strip()
        self.api_version = api_version
        self._session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{GRAPH_BASE}/{self.api_version}{path}"
        params = dict(params or {})
        params["access_token"] = self.access_token
        if method.upper() == "GET":
            r = self._session.get(url, params=params, timeout=60)
        else:
            r = self._session.post(url, params=params, json=json, timeout=60)
        r.raise_for_status()
        return r.json()

    def create_reel_container(
        self,
        video_url: str,
        caption: str = "",
    ) -> str:
        """
        Создаёт контейнер для Reels. Instagram загружает видео по video_url (должен быть публичный URL).
        Возвращает IG Container ID.
        """
        if not video_url or not video_url.strip():
            raise ValueError("video_url обязателен")
        path = f"/{self.ig_account_id}/media"
        payload: dict[str, Any] = {
            "media_type": "REELS",
            "video_url": video_url.strip(),
        }
        if caption:
            payload["caption"] = caption
        data = self._request("POST", path, json=payload)
        container_id = data.get("id")
        if not container_id:
            raise RuntimeError(f"Нет id в ответе: {data}")
        return container_id

    def get_container_status(self, container_id: str) -> str:
        """Статус контейнера: IN_PROGRESS, FINISHED, EXPIRED, ERROR, PUBLISHED."""
        path = f"/{container_id}"
        data = self._request("GET", path, params={"fields": "status_code"})
        return data.get("status_code", "")

    def wait_container_ready(
        self,
        container_id: str,
        *,
        max_wait_sec: int = 300,
        poll_interval_sec: int = 15,
    ) -> str:
        """
        Ждёт, пока контейнер станет FINISHED или ошибка/истечение.
        Возвращает итоговый status_code.
        """
        deadline = time.monotonic() + max_wait_sec
        while time.monotonic() < deadline:
            status = self.get_container_status(container_id)
            if status in ("FINISHED", "EXPIRED", "ERROR", "PUBLISHED"):
                return status
            time.sleep(poll_interval_sec)
        return self.get_container_status(container_id)

    def publish_container(self, container_id: str) -> str:
        """
        Публикует созданный контейнер.
        Возвращает Instagram Media ID.
        """
        path = f"/{self.ig_account_id}/media_publish"
        data = self._request("POST", path, json={"creation_id": container_id})
        media_id = data.get("id")
        if not media_id:
            raise RuntimeError(f"Нет id в ответе публикации: {data}")
        return media_id

    def publish_reel(
        self,
        video_url: str,
        caption: str = "",
        *,
        wait_ready: bool = True,
        max_wait_sec: int = 300,
    ) -> str:
        """
        Полный цикл: создать контейнер Reels, дождаться готовности, опубликовать.
        Возвращает Instagram Media ID опубликованного Reels.
        """
        container_id = self.create_reel_container(video_url=video_url, caption=caption)
        if wait_ready:
            status = self.wait_container_ready(
                container_id, max_wait_sec=max_wait_sec
            )
            if status != "FINISHED":
                raise RuntimeError(
                    f"Контейнер не готов к публикации: status_code={status}"
                )
        return self.publish_container(container_id)


def main() -> None:
    load_dotenv()
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "").strip()
    video_url = os.getenv("INSTAGRAM_VIDEO_URL", "").strip()

    if not token or not account_id:
        print(
            "Задайте INSTAGRAM_ACCESS_TOKEN и INSTAGRAM_ACCOUNT_ID в .env (скопируйте из .env.example).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not video_url:
        print(
            "Для теста публикации задайте INSTAGRAM_VIDEO_URL (публичная ссылка на .mp4) в .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    publisher = InstagramReelsPublisher(
        access_token=token,
        ig_account_id=account_id,
    )
    print("Создаём контейнер Reels...")
    container_id = publisher.create_reel_container(
        video_url=video_url,
        caption="Тест публикации Reels через API",
    )
    print(f"Контейнер создан: {container_id}")
    print("Ожидаем обработку видео (до 5 мин)...")
    status = publisher.wait_container_ready(container_id)
    if status != "FINISHED":
        print(f"Контейнер в состоянии {status}. Публикация отменена.", file=sys.stderr)
        sys.exit(1)
    print("Публикуем...")
    media_id = publisher.publish_container(container_id)
    print(f"Reels опубликован, media_id: {media_id}")


if __name__ == "__main__":
    main()
