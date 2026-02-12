import json
import os
import random
import time
from pathlib import Path

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

    def random_delay(self, min_delay=0.5, max_delay=5.0):
        time.sleep(random.uniform(min_delay, max_delay))

    def start(self):
        print("🚀 Помощник публикации Reels в Instagram")

        session_dir = Path(f"sessions/{self.account_name}")
        if session_dir.exists():
            print(f"📥 Загружаю кеш сессии: {session_dir}")

        self.browser = Camoufox(headless=False, humanize=True)
        self.page = self.browser.new_page()
        self.page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})

        # Загрузка кеша сессии если есть
        session_file = session_dir / "session.json"
        if session_file.exists():
            with open(session_file) as f:
                session_data = json.load(f)
            self.page.context.add_cookies(session_data.get("cookies", []))
            print("✅ Кеш сессии загружен")

        print("📱 Переходим в Instagram...")
        self.page.goto(f"https://www.instagram.com/{self.account_name}/")
        self.random_delay(1, 3)

        print("🔐 Вводи логин/пароль вручную...")

    def continue_after_login(self):
        self.save_session()

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
                except:
                    pass  # Уже открыто окно публикации

                self.random_delay()

                # Выбор файла
                upload_btn = self.page.locator(
                    'button:has-text("Выбрать на компьютере")'
                )
                upload_btn.click()
                self.random_delay(1, 2)

                # Загрузка видео
                self.page.browser_file_chooser.upload([video_path])
                self.random_delay(3, 6)

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
                next_btn1 = self.page.locator('role=button:has-text("Далее")').first
                next_btn1.click()
                self.random_delay(2, 4)

                # Далее 2
                next_btn2 = self.page.locator('role=button:has-text("Далее")').first
                next_btn2.click()
                self.random_delay(2, 4)

                # Ввод описания
                caption_input = self.page.locator('[aria-label="Добавьте подпись…"]')
                caption_input.click()
                caption_input.fill(self.description)
                self.page.keyboard.press("Escape")
                self.random_delay()

                # Поделиться
                share_btn = self.page.locator('role=button:has-text("Поделиться")')
                share_btn.click()
                self.random_delay(5, 10)

                # Ждем подтверждение публикации
                self.page.wait_for_selector('img[alt*="Галочка"]', timeout=30000)
                print("✅ Reels опубликован!")

                # Закрываем окно успеха
                close_btn = self.page.locator('svg[aria-label="Закрыть"]')
                close_btn.click()
                self.random_delay(3, 6)

            except Exception as e:
                print(
                    f"❌ Ошибка при публикации {os.path.basename(video_path)}: {str(e)}"
                )
                continue

        print("\n🎉 ГОТОВО! Все Reels опубликованы!")
        if self.browser:
            self.browser.close()
