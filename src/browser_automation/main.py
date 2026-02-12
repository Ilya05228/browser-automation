import glob
import json
import os
import random
import time
from pathlib import Path

from camoufox.sync_api import Camoufox


def save_session(page, account_name):
    session_dir = Path(f"sessions/{account_name}")
    session_dir.mkdir(parents=True, exist_ok=True)

    context_cookies = page.context.cookies()
    local_storage = page.evaluate(
        "() => Object.assign({}, ...Array.from(document.querySelectorAll('script')).map(s => ({ [s.dataset.name]: s.textContent })))"
    )

    session_data = {
        "cookies": context_cookies,
        "local_storage": local_storage,
        "user_agent": page.evaluate("() => navigator.userAgent"),
        "viewport": page.viewport_size,
    }

    with open(session_dir / "session.json", "w") as f:
        json.dump(session_data, f, indent=2)
    print(f"💾 Сессия сохранена: {session_dir}")


def random_delay(min_delay=0.5, max_delay=5.0):
    time.sleep(random.uniform(min_delay, max_delay))


def main():
    print("🚀 Помощник публикации Reels в Instagram")

    vpn_ok = input("🔒 Переключись на нужный VPN. Готов? (Y/n): ").lower() != "n"
    if not vpn_ok:
        print("❌ VPN не готов. Выход.")
        return

    video_folder = input("📁 Абсолютный путь к папке с видео: ").strip()
    if not os.path.exists(video_folder):
        print(f"❌ Папка не найдена: {video_folder}")
        return

    description = input("📝 Описание для ролика: ")
    account_name = input("👤 Имя аккаунта: ").strip().lower().replace("@", "")

    video_files = sorted(
        glob.glob(os.path.join(video_folder, "*.mp4"))
        + glob.glob(os.path.join(video_folder, "*.mov"))
    )
    if not video_files:
        print("❌ Видео файлы не найдены (*.mp4, *.mov)")
        return

    print(f"📹 Найдено {len(video_files)} видео файлов")

    session_dir = Path(f"sessions/{account_name}")
    if session_dir.exists():
        print(f"📥 Загружаю кеш сессии: {session_dir}")

    with Camoufox(headless=False, humanize=True) as browser:
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})

        # Загрузка кеша сессии если есть
        session_file = session_dir / "session.json"
        if session_file.exists():
            with open(session_file) as f:
                session_data = json.load(f)
            page.context.add_cookies(session_data.get("cookies", []))
            print("✅ Кеш сессии загружен")

        print("📱 Переходим в Instagram...")
        page.goto(f"https://www.instagram.com/{account_name}/")
        random_delay(1, 3)

        print("🔐 Вводи логин/пароль вручную...")
        input("✅ После входа нажми Enter...")

        save_session(page, account_name)

        # Основной цикл публикации
        for i, video_path in enumerate(video_files, 1):
            print(
                f"\n🎬 [{i}/{len(video_files)}] Публикуем: {os.path.basename(video_path)}"
            )
            try:
                # Кнопка "Новая публикация" (+)
                page.wait_for_selector('[aria-label="Новая публикация"]', timeout=10000)
                plus_btn = page.locator('[aria-label="Новая публикация"]')
                plus_btn.click()
                random_delay()

                # Кнопка "Публикация" в меню
                try:
                    post_btn = page.locator('text="Публикация"')
                    post_btn.click()
                except:
                    pass  # Уже открыто окно публикации

                random_delay()

                # Выбор файла
                upload_btn = page.locator('button:has-text("Выбрать на компьютере")')
                upload_btn.click()
                random_delay(1, 2)

                # Загрузка видео
                page.browser_file_chooser.upload([video_path])
                random_delay(3, 6)

                # Кнопка "Выбрать размер и обрезать"
                crop_btn = page.locator(
                    'button:has(svg[aria-label="Выбрать размер и обрезать"])'
                )
                crop_btn.click()
                random_delay()

                # Выбор "Оригинал"
                original_btn = page.locator('text="Оригинал"')
                original_btn.click()
                random_delay()

                # Далее 1
                next_btn1 = page.locator('role=button:has-text("Далее")').first
                next_btn1.click()
                random_delay(2, 4)

                # Далее 2
                next_btn2 = page.locator('role=button:has-text("Далее")').first
                next_btn2.click()
                random_delay(2, 4)

                # Ввод описания
                caption_input = page.locator('[aria-label="Добавьте подпись…"]')
                caption_input.click()
                caption_input.fill(description)
                page.keyboard.press("Escape")
                random_delay()

                # Поделиться
                share_btn = page.locator('role=button:has-text("Поделиться")')
                share_btn.click()
                random_delay(5, 10)

                # Ждем подтверждение публикации
                page.wait_for_selector('img[alt*="Галочка"]', timeout=30000)
                print("✅ Reels опубликован!")

                # Закрываем окно успеха
                close_btn = page.locator('svg[aria-label="Закрыть"]')
                close_btn.click()
                random_delay(3, 6)

            except Exception as e:
                print(
                    f"❌ Ошибка при публикации {os.path.basename(video_path)}: {str(e)}"
                )
                continue

        print("\n🎉 ГОТОВО! Все Reels опубликованы!")
        input("Press Enter to close...")
