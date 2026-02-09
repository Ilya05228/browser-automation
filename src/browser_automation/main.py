import requests
from camoufox.sync_api import Camoufox


def main():
    response = requests.get("https://httpbin.org/ip")

    my_real_ip = response.json()["origin"]
    print(f"✅ Твой IP: {my_real_ip}")
    with Camoufox(
        headless=False,
        humanize=True,
        geoip=my_real_ip,
        locale="ru-RU,en-US",
    ) as browser:
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"})
        page.goto("https://whoer.net")
        yn = input("Перейти ли в инстаграм? (y/n): ")
        if yn.lower() == "y":
            page.goto("https://www.instagram.com")
        else:
            print("Остались на whoer.net")
        input("Press Enter to close...")
