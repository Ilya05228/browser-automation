"""Пример использования InstagramPublishAction с camoufox."""

import sys
import traceback
from pathlib import Path

from camoufox import DefaultAddons
from camoufox.sync_api import Camoufox

from browser_automation.actions import InstagramPublishAction
from browser_automation.value_objects import (
    DelayRange,
    InstagramProfile,
    OnErrorBrowser,
    PhotoPath,
    PostDescription,
    VideoPath,
)


def main() -> None:
    """Основная функция с тестовыми данными."""
    # Интерактивный ввод данных
    username = input("Введите имя пользователя Instagram: ").strip()
    password = input("Введите пароль Instagram: ").strip()

    # Создаем Value Objects
    profile = InstagramProfile(username=username, password=password)
    video = VideoPath(Path("/home/ilya/Desktop/10.mp4"))
    photo = PhotoPath(Path("/home/ilya/Desktop/photo_2026-02-09_12-59-46.jpg"))
    description = PostDescription(
        "шня (Шанхай) – 632 м. Узнаваемая спиральная форма — это инженерное решение для защиты от ветра. "
        "Обладатель самых sбыстрых лифтов в мире.\n\n"
    )

    # Создаем экземпляр класса действия (0.5–2 сек между действиями)
    action = InstagramPublishAction(
        video_path=video,
        photo_path=photo,
        instagram_profile=profile,
        description=description,
        delay_between_actions=DelayRange(0.5, 2.0),
    )

    # Запускаем camoufox браузер
    print("🚀 Запуск camoufox браузера...")
    camoufox = Camoufox(
        headless=False,
        humanize=True,
        exclude_addons=[DefaultAddons.UBO],  # браузер без uBlock Origin
    )
    browser = camoufox.start()

    # При ошибке: KEEP_OPEN — не закрывать браузер, ждём Enter, потом закроем и выйдем
    on_error: OnErrorBrowser = OnErrorBrowser.KEEP_OPEN
    close_browser = True
    had_error = False

    try:
        print("📱 Начинаем публикацию в Instagram...")
        action.run(browser)
        print("✅ Публикация завершена!")
    except Exception:
        had_error = True
        traceback.print_exc(file=sys.stderr)
        if on_error == OnErrorBrowser.KEEP_OPEN:
            close_browser = False
            print("🔍 Браузер оставлен открытым. Посмотри страницу, затем нажми Enter здесь — тогда браузер закроется и выйдем.", file=sys.stderr)
            input()
            close_browser = True
        else:
            pass  # close_browser уже True
    finally:
        if close_browser:
            browser.close()
            print("🔒 Браузер закрыт")

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
