import logging
import logging.handlers
import json
import threading
import asyncio
import sys
import gc
import os

import bot

conf = json.loads(open("config.json", 'r').read())

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
    filename="leatest.log",
    encoding="utf-8",
    maxBytes=1024 * 1024 * conf['log_file_size_mb'],
    backupCount=conf['log_backup_count'],
)

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt=conf['datefmt']
)
handler.setFormatter(formatter)
logger.addHandler(handler)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def console():
    try:
        while True:
            cmd = input(">> ").strip()
            if cmd == "stop":
                print("Stopping bot...")

                async def shutdown():
                    try:
                        await bot.bot.close()
                        await asyncio.sleep(0.5)  # Let aiohttp shut down
                        pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
                        if pending:
                            print(f"Waiting for {len(pending)} tasks...")
                            await asyncio.gather(*pending, return_exceptions=True)
                    except Exception as e:
                        print(f"Exception in shutdown: {e}")
                    finally:
                        loop.stop()

                asyncio.run_coroutine_threadsafe(shutdown(), loop)
                break

            else:
                print(f"Unknown command: {cmd}. Enter help to list the commands.")

    except KeyboardInterrupt:
        print("\nConsole thread exiting.")

def run():
    t = threading.Thread(target=console, name="ConsoleThread", daemon=True)
    t.start()
    try:
        coro = bot.run_bot(loop)
        if not asyncio.iscoroutine(coro):
            raise TypeError("bot.run_bot() must be a coroutine")
        loop.run_until_complete(coro)
        loop.run_forever()  # Allow shutdown() coroutine to run
    finally:
        # Ensure loop is not already closed
        if not loop.is_closed():
            loop.close()
        gc.collect()
        print("Event loop closed.")

if __name__ == "__main__":
    run()
