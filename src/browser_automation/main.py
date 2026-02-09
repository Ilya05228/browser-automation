import requests
from camoufox.sync_api import Camoufox


def main():
    response = requests.get("https://httpbin.org/ip")

    my_real_ip = response.json()["origin"]
    print(f"✅ Твой IP: {my_real_ip}")

    warm_up_sites = [
        # "https://habr.com",
        # "https://lenta.ru",
        "https://www.bbc.com/news",
    ]

    with Camoufox(
        headless=False,
        humanize=True,
        geoip=my_real_ip,
        locale="ru-RU,en-US",
    ) as browser:
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})

        print("🔍 Проверяем fingerprint на whoer.net...")
        page.goto("https://whoer.net")
        input("✅ Проверь whoer.net score! Press Enter для warm-up...")
        print(f"🌡️  Warm-up: собираем cookies с {len(warm_up_sites)} сайтов...")
        for i, site in enumerate(warm_up_sites, 1):
            print(f"📱 [{i}/{len(warm_up_sites)}] Загружаем {site}...")
            page.goto(site)
            page.wait_for_timeout(2000)  # 2 сек
            page.mouse.wheel(0, 200)  # Скролл вниз
            page.wait_for_timeout(1000)  # 1 сек пауза

            print(f"   ✅ Cookies собраны с {site}")

        yn = input("Перейти ли в инстаграм с warm-up? (y/n): ")
        if yn.lower() == "y":
            print("📸 Переходим в Instagram с теплыми cookies!")
            page.goto("https://www.instagram.com")
        else:
            print("Остались на whoer.net")

        input("Press Enter to close...")
