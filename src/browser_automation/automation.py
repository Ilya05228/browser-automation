import asyncio
import json
import os
import random
import time
from pathlib import Path

from camoufox.async_api import AsyncCamoufox
from camoufox.sync_api import Camoufox


class Automation:
    def __init__(self, description, video_files, account_name):
        self.description = description
        self.video_files = video_files
        self.account_name = account_name
        self.browser = None
        self.page = None

    def save_session(self):
        session_dir = Path(f"sessions/{self.account_name}")
        session_dir.mkdir(parents=True, exist_ok=True)

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

        with open(session_dir / "session.json", "w") as f:
            json.dump(session_data, f, indent=2)
        print(f"💾 Сессия сохранена: {session_dir}")

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
        self.page.set_extra_http_headers(
            {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
        )
        session_dir = Path(f"sessions/{self.account_name}")
        session_file = session_dir / "session.json"
        if session_file.exists():
            with open(session_file) as f:
                session_data = json.load(f)
            self.page.context.add_cookies(session_data.get("cookies", []))
            print("✅ Кеш сессии загружен")
        print("📱 Открываю Instagram...")
        self.page.goto("https://www.instagram.com/")
        self.random_delay()

    def continue_after_login(self):
        """Сохраняем сессию из видимого браузера, переходим в headless и публикуем.
        В headless пользователь не может перехватить управление.
        Возвращает True если все Reels опубликованы, False если были ошибки.
        """
        session_dir = Path(f"sessions/{self.account_name}")
        session_file = session_dir / "session.json"

        if self.page is None:
            raise RuntimeError("Сначала нажмите 'Начать' и дождитесь открытия браузера")

        self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        self.random_delay()
        self.save_session()

        # Закрываем видимый браузер и продолжаем в headless — пользователь не сможет мешать
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None

        camoufox = Camoufox(headless=True, humanize=True)
        self.browser = camoufox.start()
        self.page = self.browser.new_page()
        self.page.set_extra_http_headers(
            {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
        )
        with open(session_file) as f:
            session_data = json.load(f)
        self.page.context.add_cookies(session_data.get("cookies", []))
        self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        self.random_delay()

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

                # Загрузка файла через ожидание file chooser (без перехвата нативного диалога)
                upload_btn = self.page.locator(
                    'button:has-text("Выбрать на компьютере")'
                )
                with self.page.expect_file_chooser() as fc_info:
                    upload_btn.click()
                fc_info.value.set_files([video_path])
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
                caption_input = self.page.locator(
                    '[aria-label="Добавьте подпись…"]'
                )
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
        print(f"\n⚠️ Завершено с ошибками: не опубликовано {failed_count} из {len(self.video_files)}")
        return False

    # --- Async API (избегаем "Sync API inside asyncio loop" в дочернем процессе) ---

    async def _random_delay_async(self, min_delay=0.5, max_delay=3.0):
        await asyncio.sleep(random.uniform(min_delay, max_delay))

    async def save_session_async(self):
        session_dir = Path(f"sessions/{self.account_name}")
        session_dir.mkdir(parents=True, exist_ok=True)
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
        with open(session_dir / "session.json", "w") as f:
            json.dump(session_data, f, indent=2)
        print(f"💾 Сессия сохранена: {session_dir}")

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
        session_dir = Path(f"sessions/{self.account_name}")
        session_file = session_dir / "session.json"
        if session_file.exists():
            with open(session_file) as f:
                session_data = json.load(f)
            await self.page.context.add_cookies(session_data.get("cookies", []))
            print("✅ Кеш сессии загружен")
        print("📱 Открываю Instagram...")
        await self.page.goto("https://www.instagram.com/")
        await self._random_delay_async()

    async def continue_after_login_async(self):
        """Сохраняем сессию, перезапускаем браузер в видимом режиме и публикуем.
        Браузер виден, но не трогайте его — иначе публикация собьётся."""
        session_dir = Path(f"sessions/{self.account_name}")
        session_file = session_dir / "session.json"
        if self.page is None:
            raise RuntimeError("Сначала нажмите 'Начать' и дождитесь открытия браузера")
        await self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        await self._random_delay_async()
        await self.save_session_async()
        if hasattr(self, "_camoufox_cm"):
            await self._camoufox_cm.__aexit__(None, None, None)
            del self._camoufox_cm
        self.browser = None
        self.page = None

        print("📺 Открываю браузер для публикации (не трогайте окно — идёт автоматизация)")
        self._camoufox_cm2 = AsyncCamoufox(headless=False, humanize=True)
        self.browser = await self._camoufox_cm2.__aenter__()
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers(
            {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
        )
        with open(session_file) as f:
            session_data = json.load(f)
        await self.page.context.add_cookies(session_data.get("cookies", []))
        await self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        await self._random_delay_async()

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

                # Ждём модалку «Создание публикации»
                await self.page.locator('[aria-label="Создание публикации"]').wait_for(
                    state="visible", timeout=15000
                )
                await self._random_delay_async()

                # Сначала пробуем задать файл напрямую в input
                file_done = False
                try:
                    file_input = self.page.locator(
                        'form[enctype="multipart/form-data"] input[type=file]'
                    ).first
                    await file_input.wait_for(state="attached", timeout=6000)
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
                    # Иначе открываем выбор файла через кнопку (file chooser)
                    async with self.page.expect_file_chooser(timeout=15000) as fc_info:
                        await self.page.locator(
                            'button:has-text("Выбрать на компьютере"), button:has-text("Select from computer")'
                        ).first.click(force=True)
                    file_chooser = await fc_info.value
                    await file_chooser.set_files([video_path])

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

                caption_input = self.page.locator(
                    '[aria-label="Добавьте подпись…"]'
                )
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
        print(f"\n⚠️ Завершено с ошибками: не опубликовано {failed_count} из {len(self.video_files)}")
        return False
