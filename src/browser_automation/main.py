from camoufox.sync_api import Camoufox

with Camoufox(headless=False, humanize=True, geoip=True) as browser:
    page = browser.new_page()
    page.goto("https://whoer.net")
    # page.goto("https://www.instagram.com/?hl=ru")

    input("Press Enter to close...")
