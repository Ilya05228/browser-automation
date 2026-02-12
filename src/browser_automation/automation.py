import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

from camoufox.async_api import AsyncCamoufox
from camoufox.sync_api import Camoufox
from playwright.sync_api import (
    Browser,
    Page,
)

logger = logging.getLogger(__name__)


class Automation:
    def __init__(self, description, video_files, account_name):
        self.description = description
        self.video_files = video_files
        self.account_name = account_name
        self.browser: Browser = None
        self.page: Page = None

    def save_session(self):
        cache_file = Path("cache") / "sessions.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        context_cookies = self.page.context.cookies()
        local_storage = self.page.evaluate(
            "() => Object.assign({}, ...Array.from(document.querySelectorAll('script')).map(s => ({ [s.dataset.name]: s.textContent })))"
        )

        session_data = {
            "cookies": context_cookies,
            "local_storage": local_storage,
            "user_agent": self.page.evaluate("() => navigator.userAgent"),
            "viewport": self.page.viewport_size,
        }

        # Загружаем существующие сессии или создаём новый словарь
        all_sessions = {}
        if cache_file.exists():
            with open(cache_file) as f:
                all_sessions = json.load(f)

        # Сохраняем сессию по ключу (имя канала)
        all_sessions[self.account_name] = session_data

        with open(cache_file, "w") as f:
            json.dump(all_sessions, f, indent=2)
        print(f"💾 Сессия сохранена для канала '{self.account_name}' в {cache_file}")

    def random_delay(self, min_delay=0.5, max_delay=3.0):
        time.sleep(random.uniform(min_delay, max_delay))

    def start(self):
        print("🚀 Помощник публикации Reels в Instagram")
        print("✅ Переключи VPN и открой Instagram вручную")
        print("🔐 Войди в аккаунт")
        print("➡️ Нажми 'Продолжить' в интерфейсе")

        # Camoufox(): .start() возвращает Playwright Browser с методом new_page()
        camoufox = Camoufox(headless=False, humanize=True)
        self.browser = camoufox.start()
        self.page = self.browser.new_page()
        self.page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})
        cache_file = Path("cache") / "sessions.json"
        if cache_file.exists():
            with open(cache_file) as f:
                all_sessions = json.load(f)
            session_data = all_sessions.get(self.account_name)
            if session_data:
                self.page.context.add_cookies(session_data.get("cookies", []))
                print(f"✅ Кеш сессии загружен для канала '{self.account_name}'")
        print("📱 Открываю Instagram...")
        self.page.goto("https://www.instagram.com/")
        self.random_delay()

    def continue_after_login(self):
        """Сохраняем сессию и публикуем в текущей вкладке браузера.
        Возвращает True если все Reels опубликованы, False если были ошибки.
        """
        if self.page is None:
            raise RuntimeError("Сначала нажмите 'Начать' и дождитесь открытия браузера")

        self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        self.random_delay()
        self.save_session()

        failed_count = 0
        # Основной цикл публикации
        for i, video_path in enumerate(self.video_files, 1):
            print(
                f"\n🎬 [{i}/{len(self.video_files)}] Публикуем: {os.path.basename(video_path)}"
            )
            try:
                # Кнопка "Новая публикация" (+)
                self.page.wait_for_selector(
                    '[aria-label="Новая публикация"]', timeout=10000
                )
                plus_btn = self.page.locator('[aria-label="Новая публикация"]')
                plus_btn.click()
                self.random_delay()

                # Кнопка "Публикация" в меню
                try:
                    post_btn = self.page.locator('text="Публикация"')
                    post_btn.click()
                except Exception:
                    pass  # Уже открыто окно публикации

                self.random_delay()

                # Загрузка файла в input[type=file]
                logger.info("Ожидаем поле выбора файла (до 5 секунд)...")
                self.page.wait_for_selector(
                    'form[enctype="multipart/form-data"] input[type=file]', timeout=5000
                )
                logger.info(f"Вставляем файл в форму: {os.path.basename(video_path)}")
                self.page.set_input_files(
                    'form[enctype="multipart/form-data"] input[type=file]',
                    [video_path],
                )
                self.page.evaluate(
                    """
                    () => {
                      const input = document.querySelector('form[enctype="multipart/form-data"] input[type=file]');
                      if (input) input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                self.random_delay()

                # Кнопка "Выбрать размер и обрезать"
                crop_btn = self.page.locator(
                    'button:has(svg[aria-label="Выбрать размер и обрезать"])'
                )
                crop_btn.click()
                self.random_delay()

                # Выбор "Оригинал"
                original_btn = self.page.locator('text="Оригинал"')
                original_btn.click()
                self.random_delay()

                # Далее 1
                next_btn1 = self.page.get_by_role("button", name="Далее").first
                next_btn1.click()
                self.random_delay()

                # Далее 2
                next_btn2 = self.page.get_by_role("button", name="Далее").first
                next_btn2.click()
                self.random_delay()

                # Ввод описания
                caption_input = self.page.locator('[aria-label="Добавьте подпись…"]')
                caption_input.click()
                caption_input.fill(self.description)
                self.page.keyboard.press("Escape")
                self.random_delay()

                # Поделиться
                share_btn = self.page.get_by_role("button", name="Поделиться")
                share_btn.click()
                self.random_delay()

                # Ждем подтверждение публикации
                self.page.wait_for_selector('img[alt*="Галочка"]', timeout=30000)
                print("✅ Reels опубликован!")

                # Закрываем окно успеха
                close_btn = self.page.locator('svg[aria-label="Закрыть"]')
                close_btn.click()
                self.random_delay()

            except Exception as e:
                failed_count += 1
                print(
                    f"❌ Ошибка при публикации {os.path.basename(video_path)}: {str(e)}"
                )
                continue

        if failed_count == 0:
            print("\n🎉 ГОТОВО! Все Reels опубликованы!")
            return True
        print(
            f"\n⚠️ Завершено с ошибками: не опубликовано {failed_count} из {len(self.video_files)}"
        )
        return False

    # --- Async API (избегаем "Sync API inside asyncio loop" в дочернем процессе) ---

    async def _random_delay_async(self, min_delay=0.5, max_delay=3.0):
        await asyncio.sleep(random.uniform(min_delay, max_delay))

    async def save_session_async(self):
        cache_file = Path("cache") / "sessions.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        context_cookies = await self.page.context.cookies()
        local_storage = await self.page.evaluate(
            "() => Object.assign({}, ...Array.from(document.querySelectorAll('script')).map(s => ({ [s.dataset.name]: s.textContent })))"
        )
        user_agent = await self.page.evaluate("() => navigator.userAgent")
        viewport = self.page.viewport_size
        session_data = {
            "cookies": context_cookies,
            "local_storage": local_storage,
            "user_agent": user_agent,
            "viewport": viewport,
        }

        # Загружаем существующие сессии или создаём новый словарь
        all_sessions = {}
        if cache_file.exists():
            with open(cache_file) as f:
                all_sessions = json.load(f)

        # Сохраняем сессию по ключу (имя канала)
        all_sessions[self.account_name] = session_data

        with open(cache_file, "w") as f:
            json.dump(all_sessions, f, indent=2)
        print(f"💾 Сессия сохранена для канала '{self.account_name}' в {cache_file}")

    async def start_async(self):
        print("🚀 Помощник публикации Reels в Instagram")
        print("✅ Переключи VPN и открой Instagram вручную")
        print("🔐 Войди в аккаунт")
        print("➡️ Нажми 'Продолжить' в интерфейсе")
        self._camoufox_cm = AsyncCamoufox(headless=False, humanize=True)
        self.browser = await self._camoufox_cm.__aenter__()
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers(
            {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
        )
        cache_file = Path("cache") / "sessions.json"
        if cache_file.exists():
            with open(cache_file) as f:
                all_sessions = json.load(f)
            session_data = all_sessions.get(self.account_name)
            if session_data:
                await self.page.context.add_cookies(session_data.get("cookies", []))
                print(f"✅ Кеш сессии загружен для канала '{self.account_name}'")
        print("📱 Открываю Instagram...")
        await self.page.goto("https://www.instagram.com/")
        await self._random_delay_async()

    async def continue_after_login_async(self):
        """Сохраняем сессию и публикуем в текущей вкладке браузера.
        Браузер виден, но не трогайте его — иначе публикация собьётся."""
        if self.page is None:
            raise RuntimeError("Сначала нажмите 'Начать' и дождитесь открытия браузера")
        await self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        await self._random_delay_async()
        await self.save_session_async()

        failed_count = 0
        for i, video_path in enumerate(self.video_files, 1):
            print(
                f"\n🎬 [{i}/{len(self.video_files)}] Публикуем: {os.path.basename(video_path)}"
            )
            try:
                await self.page.wait_for_selector(
                    '[aria-label="Новая публикация"]', timeout=20000
                )
                plus_btn = self.page.locator('[aria-label="Новая публикация"]')
                await plus_btn.click()
                await self._random_delay_async()

                try:
                    post_btn = self.page.locator('text="Публикация"')
                    await post_btn.click()
                except Exception:
                    pass
                await self._random_delay_async()

                # Блок загрузки файла
                logger.info("Ожидаем кнопку загрузки видео...")
                await self.page.locator('[aria-label="Создание публикации"]').wait_for(
                    state="visible", timeout=5000
                )
                await self._random_delay_async()

                logger.info("Загружаем файл...")
                # Сначала пробуем задать файл напрямую в input
                file_done = False
                try:
                    file_input = self.page.locator(
                        'form[enctype="multipart/form-data"] input[type=file]'
                    ).first
                    await file_input.wait_for(state="attached", timeout=5000)
                    await file_input.set_input_files([video_path])
                    await self.page.evaluate(
                        """
                        () => {
                          const input = document.querySelector('form[enctype="multipart/form-data"] input[type=file]');
                          if (input) input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        """
                    )
                    file_done = True
                except Exception:
                    pass

                if not file_done:
                    # Fallback: используем set_input_files напрямую с селектором
                    await self.page.set_input_files(
                        'form[enctype="multipart/form-data"] input[type=file]',
                        [video_path],
                    )
                    await self.page.evaluate(
                        """
                        () => {
                          const input = document.querySelector('form[enctype="multipart/form-data"] input[type=file]');
                          if (input) input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        """
                    )

                # Даём время на обработку видео (blob/rupload), потом ждём экран обрезки
                await asyncio.sleep(8)
                crop_btn = self.page.locator(
                    'button:has(svg[aria-label="Выбрать размер и обрезать"]), '
                    'button:has(svg[aria-label="Select size and trim"])'
                ).first
                await crop_btn.wait_for(state="visible", timeout=90000)
                await crop_btn.click()
                await self._random_delay_async()

                original_btn = self.page.locator('text="Оригинал"')
                await original_btn.click()
                await self._random_delay_async()

                next_btn1 = self.page.get_by_role("button", name="Далее").first
                await next_btn1.click()
                await self._random_delay_async()

                next_btn2 = self.page.get_by_role("button", name="Далее").first
                await next_btn2.click()
                await self._random_delay_async()

                caption_input = self.page.locator('[aria-label="Добавьте подпись…"]')
                await caption_input.click()
                await caption_input.fill(self.description)
                await self.page.keyboard.press("Escape")
                await self._random_delay_async()

                share_btn = self.page.get_by_role("button", name="Поделиться")
                await share_btn.click()
                await self._random_delay_async()

                await self.page.wait_for_selector('img[alt*="Галочка"]', timeout=60000)
                print("✅ Reels опубликован!")

                close_btn = self.page.locator('svg[aria-label="Закрыть"]')
                await close_btn.click()
                await self._random_delay_async()

            except Exception as e:
                failed_count += 1
                print(
                    f"❌ Ошибка при публикации {os.path.basename(video_path)}: {str(e)}"
                )
                continue

        if hasattr(self, "_camoufox_cm2"):
            await self._camoufox_cm2.__aexit__(None, None, None)

        if failed_count == 0:
            print("\n🎉 ГОТОВО! Все Reels опубликованы!")
            return True
        print(
            f"\n⚠️ Завершено с ошибками: не опубликовано {failed_count} из {len(self.video_files)}"
        )
        return False
