"""
Воркер для запуска в отдельном процессе (multiprocessing).
Использует Async API Playwright/Camoufox, чтобы избежать ошибки
"Sync API inside the asyncio loop".
"""
import asyncio
import json
import traceback
from pathlib import Path

from camoufox.async_api import AsyncCamoufox


async def _run_async(in_queue, out_queue, description, video_files, account_name):
    from .automation import Automation

    automation = Automation(description, list(video_files), account_name)
    out_queue.put(("status", "Запуск браузера..."))
    await automation.start_async()
    out_queue.put(("status", "Войдите в аккаунт Instagram, затем нажмите 'Продолжить'"))
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, in_queue.get)
    out_queue.put(("status", "Публикация Reels... Не трогайте браузер!"))
    ok = await automation.continue_after_login_async()
    if ok:
        out_queue.put(("status", "Все Reels опубликованы!"))
        out_queue.put(("finished", True))
    else:
        out_queue.put(("error", "Некоторые Reels не удалось опубликовать. См. вывод в консоли."))


async def _run_open_instagram_async(out_queue, account_name):
    """Запускает браузер и работает постоянно, периодически обновляя куки."""
    from .automation import Automation

    automation = Automation("", [], account_name)
    out_queue.put(("status", f"Запуск браузера для {account_name}..."))
    
    # Открываем браузер
    print(f"🚀 Открываю Instagram для входа ({account_name})...")
    automation._camoufox_cm = AsyncCamoufox(headless=False, humanize=True)
    automation.browser = await automation._camoufox_cm.__aenter__()
    automation.page = await automation.browser.new_page()
    await automation.page.set_extra_http_headers(
        {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
    )
    
    # Загружаем сохранённую сессию, если есть
    cache_file = Path("cache") / "sessions.json"
    if cache_file.exists():
        with open(cache_file) as f:
            all_sessions = json.load(f)
        session_data = all_sessions.get(account_name)
        if session_data:
            await automation.page.context.add_cookies(session_data.get("cookies", []))
            print(f"✅ Кеш сессии загружен для канала '{account_name}'")
    
    # Открываем страницу логина
    print("📱 Открываю страницу логина Instagram...")
    await automation.page.goto(
        "https://www.instagram.com/accounts/login/",
        wait_until="domcontentloaded",
        timeout=60000
    )
    await automation._random_delay_async()
    
    out_queue.put(("status", f"Браузер открыт для {account_name}. Войдите в аккаунт."))
    
    # Ждём входа (опционально)
    try:
        await automation.page.wait_for_selector(
            '[aria-label="Новая публикация"], [aria-label="Home"], a[href*="/accounts/edit/"]',
            timeout=300000  # до 5 минут на вход
        )
        print("✅ Вход выполнен! Сохраняю сессию...")
        await automation.save_session_async()
        out_queue.put(("status", f"Вход выполнен для {account_name}. Сессия сохранена."))
    except Exception:
        # Если не удалось определить вход, просто продолжаем
        print("⚠️ Ожидание входа...")
        await automation.save_session_async()
    
    # Периодически обновляем куки каждую минуту
    out_queue.put(("status", f"Браузер работает для {account_name}. Куки обновляются каждую минуту."))
    out_queue.put(("finished", True))
    
    # Бесконечный цикл для периодического обновления куков
    while True:
        try:
            # Проверяем, что браузер ещё открыт
            if not automation.browser or not automation.browser.is_connected():
                print(f"⚠️ Браузер для {account_name} закрыт. Сохраняю финальную сессию...")
                try:
                    if automation.page:
                        await automation.save_session_async()
                except Exception:
                    pass
                break
            
            # Проверяем, что страница ещё открыта
            if not automation.page or automation.page.is_closed():
                print(f"⚠️ Страница для {account_name} закрыта. Пытаюсь переоткрыть...")
                try:
                    # Пытаемся переоткрыть страницу
                    automation.page = await automation.browser.new_page()
                    await automation.page.set_extra_http_headers(
                        {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
                    )
                    await automation.page.goto(
                        "https://www.instagram.com/",
                        wait_until="domcontentloaded",
                        timeout=60000
                    )
                    print(f"✅ Страница переоткрыта для {account_name}")
                except Exception as e:
                    print(f"⚠️ Не удалось переоткрыть страницу для {account_name}: {e}")
                    await asyncio.sleep(60)
                    continue
            
            # Ждём минуту
            await asyncio.sleep(60)
            
            # Обновляем куки
            if automation.page and not automation.page.is_closed():
                print(f"🔄 Обновляю куки для {account_name}...")
                try:
                    await automation.save_session_async()
                    print(f"✅ Куки обновлены для {account_name}")
                except Exception as e:
                    print(f"⚠️ Ошибка при сохранении куков для {account_name}: {e}")
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении куков для {account_name}: {e}")
            # Продолжаем работу даже при ошибке
            await asyncio.sleep(60)


def run_worker(in_queue, out_queue, description, video_files, account_name):
    """Точка входа для subprocess. Запускает async-автоматизацию в asyncio.run()."""
    try:
        asyncio.run(_run_async(in_queue, out_queue, description, video_files, account_name))
    except Exception as e:
        out_queue.put(("error", f"{str(e)}\n\n{traceback.format_exc()}"))
    finally:
        out_queue.put(("done",))


async def _run_antidetect_browser_async(out_queue):
    """Запускает антидетект браузер без куков и сессий."""
    print("🚀 Открываю антидетект браузер...")
    
    # Создаём новый браузер без загрузки куков
    camoufox_cm = AsyncCamoufox(headless=False, humanize=True)
    browser = await camoufox_cm.__aenter__()
    page = await browser.new_page()
    await page.set_extra_http_headers(
        {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
    )
    
    # Открываем главную страницу Instagram (без логина)
    print("📱 Открываю Instagram...")
    await page.goto(
        "https://www.instagram.com/",
        wait_until="domcontentloaded",
        timeout=60000
    )
    
    out_queue.put(("status", "Антидетект браузер открыт (без куков и сессий)"))
    out_queue.put(("finished", True))
    
    # Браузер остаётся открытым до закрытия пользователем
    # Просто ждём, пока браузер не закроется
    while True:
        try:
            if not browser or not browser.is_connected():
                print("⚠️ Браузер закрыт.")
                break
            await asyncio.sleep(5)  # Проверяем каждые 5 секунд
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            break


def run_open_instagram_worker(out_queue, account_name):
    """Воркер для открытия Instagram и сохранения сессии."""
    try:
        asyncio.run(_run_open_instagram_async(out_queue, account_name))
    except Exception as e:
        out_queue.put(("error", f"{str(e)}\n\n{traceback.format_exc()}"))
    finally:
        out_queue.put(("done",))


def run_antidetect_browser_worker(out_queue):
    """Воркер для открытия антидетект браузера без куков."""
    try:
        asyncio.run(_run_antidetect_browser_async(out_queue))
    except Exception as e:
        out_queue.put(("error", f"{str(e)}\n\n{traceback.format_exc()}"))
    finally:
        out_queue.put(("done",))
