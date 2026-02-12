"""
Воркер для запуска в отдельном процессе (multiprocessing).
Использует Async API Playwright/Camoufox, чтобы избежать ошибки
"Sync API inside the asyncio loop".
"""
import asyncio
import traceback


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


def run_worker(in_queue, out_queue, description, video_files, account_name):
    """Точка входа для subprocess. Запускает async-автоматизацию в asyncio.run()."""
    try:
        asyncio.run(_run_async(in_queue, out_queue, description, video_files, account_name))
    except Exception as e:
        out_queue.put(("error", f"{str(e)}\n\n{traceback.format_exc()}"))
    finally:
        out_queue.put(("done",))
