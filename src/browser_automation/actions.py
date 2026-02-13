import random
import time
from pathlib import Path

from camoufox import DefaultAddons
from camoufox.sync_api import Camoufox
from playwright.sync_api import Browser

from browser_automation.value_objects import (
    DelayRange,
    InstagramProfile,
    PhotoPath,
    PostDescription,
    VideoPath,
)


class InstagramPublishAction:
    """Класс публикации в Instagram: принимает путь к видео, путь к фото и профиль (VO)."""

    def __init__(
        self,
        *,
        video_path: VideoPath,
        photo_path: PhotoPath,
        instagram_profile: InstagramProfile,
        description: PostDescription,
        delay_between_actions: DelayRange | None = None,
    ) -> None:
        self.video_path = video_path
        self.photo_path = photo_path
        self.profile = instagram_profile
        self.description = description
        self.delay = delay_between_actions or DelayRange(0.5, 2.0)

    def _sleep(self) -> None:
        time.sleep(random.uniform(self.delay.min_sec, self.delay.max_sec))

    def run(self, browser: Browser) -> None:
        """Запускает публикацию с использованием переданного браузера (например, из camoufox)."""
        profile_name = self.profile.username
        password = self.profile.password
        video_path: Path = self.video_path.path
        photo_path: Path = self.photo_path.path

        context = browser.new_context()
        page = context.new_page()
        page.set_extra_http_headers({"Accept-Language": "ru-BY,ru;q=0.9"})
        page.goto("https://www.instagram.com/accounts/login/")
        self._sleep()
        # Две варианта формы входа: длинный label (email) и короткий (username) — подбираем оба
        username_input = page.locator(
            'input[type="text"][name="username"], input[type="text"][name="email"]'
        ).first
        username_input.fill(profile_name)
        self._sleep()
        # Пароль: в одной форме name="pass", в другой name="password"
        password_input = page.locator(
            'input[type="password"][name="password"], input[type="password"][name="pass"]'
        ).first
        password_input.fill(password)
        self._sleep()
        # Кнопка входа: и role="button", и type="submit" с текстом "Войти"
        page.get_by_role("button", name="Войти", exact=True).or_(
            page.locator('form button[type="submit"]')
        ).first.click()
        self._sleep()
        page.goto("https://www.instagram.com/accounts/onetap/")
        self._sleep()
        page.get_by_role("button", name="Не сейчас").click()
        self._sleep()
        page.get_by_role("link", name=f"Фото профиля {profile_name} Профиль").click()
        self._sleep()
        page.get_by_role("link", name="Новая публикация Создать").click()
        self._sleep()
        page.get_by_role("link", name="Публикация Публикация").click()
        self._sleep()
        page.get_by_role("button", name="Выбрать на компьютере").click()
        self._sleep()
        page.get_by_role("button", name="Выбрать на компьютере").set_input_files(
            str(video_path)
        )
        self._sleep()
        page.get_by_role("button", name="OK").click()
        self._sleep()
        page.locator("button").filter(has_text="Выбрать размер и обрезать").click()
        self._sleep()
        page.get_by_role("button", name="Оригинал Значок контура фото").click()
        self._sleep()
        page.get_by_role("button", name="Далее").click()
        self._sleep()
        page.get_by_role("button", name="Выбрать на компьютере").click()
        self._sleep()
        page.get_by_role("button", name="Выбрать на компьютере").set_input_files(
            str(photo_path)
        )
        self._sleep()
        page.get_by_role("button", name="Далее").click()
        self._sleep()
        page.get_by_role("textbox", name="Добавьте подпись…").click()
        self._sleep()
        page.get_by_role("paragraph").click()
        self._sleep()
        page.get_by_role("textbox", name="Добавьте подпись…").fill(self.description.text)
        self._sleep()
        page.get_by_role("button", name="Поделиться").click()
        self._sleep()
        page.get_by_role("button", name="Закрыть").click()
        self._sleep()
        page.get_by_role("link", name="Новая публикация Создать").click()

        context.close()


if __name__ == "__main__":
    profile = InstagramProfile(username="fast.funnne", password="MYPASSSWORD")
    video = VideoPath(Path("10.mp4"))
    photo = PhotoPath(Path("photo_2026-02-09_12-59-46.jpg"))
    description = PostDescription(
        "шня (Шанхай) – 632 м. Узнаваемая спиральная форма — это инженерное решение для защиты от ветра. "
        "Обладатель самых sбыстрых лифтов в мире.\n\n"
    )

    action = InstagramPublishAction(
        video_path=video,
        photo_path=photo,
        instagram_profile=profile,
        description=description,
        delay_between_actions=DelayRange(0.5, 2.0),
    )

    camoufox = Camoufox(
        headless=False,
        humanize=True,
        exclude_addons=[DefaultAddons.UBO],
    )
    browser = camoufox.start()
    try:
        action.run(browser)
    finally:
        browser.close()
