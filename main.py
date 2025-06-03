import logging
import logging.handlers
import json
import threading

import bot

config = json.loads(open("config.json", 'r').read())
threads = []

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
    filename="leatest.log",
    encoding="utf-8",
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=5,
)

dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt=dt_fmt
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def run():
    t = threading.Thread(target=bot.run_bot, name="BotThread", daemon=True)
    t.start()
    t.join()
    # threads.append(t)

    # for t in threads:
    #     t.start()

    # input("Press Enter to exit...")

    # for t in threads:
    #     t.join()

if __name__ == "__main__":
    run()
