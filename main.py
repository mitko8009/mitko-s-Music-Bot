import logging
import logging.handlers
import colorlog
import json
import threading
import asyncio
import gc
import sys

from PyQt5 import QtWidgets, uic

import bot

class MusicBotApp:
    def __init__(self):
        self.conf = json.loads(open("config.json", 'r').read())
        self.logger = self.setup_logger()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.console_thread = None

    def setup_logger(self):
        logger = logging.getLogger("discord")
        logger.setLevel(logging.DEBUG if self.conf['debug'] else logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename=self.conf['logging']['file'],
            encoding="utf-8",
            maxBytes=1024 * 1024 * self.conf['logging']['file_size_mb'],
            backupCount=self.conf['logging']['backup_count'],
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt=self.conf["logging"]['datefmt']
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Console logging
        logging.getLogger().handlers.clear()
        console_handler = colorlog.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            fmt="%(asctime_log_color)s%(asctime)s%(reset)s | "
                "%(log_color)s%(levelname)-8s%(reset)s| "
                "%(name_log_color)s%(name)s%(reset)s: %(message)s",
            datefmt=self.conf["logging"]['datefmt'],
            log_colors={
                'DEBUG': 'green',
                'INFO': 'cyan',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
            secondary_log_colors={
                "asctime": {
                    "DEBUG": "thin_white",
                    "INFO": "thin_white",
                    "WARNING": "thin_white",
                    "ERROR": "thin_white",
                    "CRITICAL": "thin_white",
                },
                "name": {
                    'DEBUG': 'green',
                    'INFO': 'white',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'bold_red',
                }
            })
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def stop_bot(self):
        self.logger.info("Stopping bot...")

        async def shutdown():
            try:
                await bot.bot.close()
                await asyncio.sleep(0.5)
                pending = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task(self.loop)]
                if pending:
                    self.logger.info(f"Waiting for {len(pending)} tasks to complete before shutdown.")
                    await asyncio.gather(*pending, return_exceptions=True)
            except Exception as e:
                self.logger.error(f"Exception during shutdown: {e}")
            finally:
                self.loop.stop()

        asyncio.run_coroutine_threadsafe(shutdown(), self.loop)

    def console(self):
        try:
            while True:
                cmd = input(">> ").strip()
                if cmd == "stop":
                    self.stop_bot()
                    break
                elif cmd == "test":
                    print("This is e test message to teset the logging!")
                    self.logger.debug("Debug message")
                    self.logger.info("Info message")
                    self.logger.warning("Warning!")
                    self.logger.error("Something went wrong")
                    self.logger.critical("CRITICAL ERROR!")
                
                else:
                    print(f"\033[93mUnknown command: \033[91m{cmd}\033[0m")
        except KeyboardInterrupt:
            self.logger.info("Console interrupted by user.")

    def run(self):
        self.console_thread = threading.Thread(target=self.console, name="ConsoleThread", daemon=True)
        self.console_thread.start()
        try:
            coro = bot.run_bot(self.loop)
            if not asyncio.iscoroutine(coro):
                raise TypeError("bot.run_bot() must be a coroutine")
            self.loop.run_until_complete(coro)
            self.loop.run_forever()
        finally:
            if not self.loop.is_closed():
                self.loop.close()
            gc.collect()
            self.logger.info("Event loop closed.")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app_logic):
        super().__init__()
        self.app_logic = app_logic
        self.init_ui()

    def init_ui(self):
        uic.loadUi("ui/main.ui", self)
        self.button.clicked.connect(self.on_stop)

    def on_stop(self):
        self.app_logic.stop_bot()
        QtWidgets.QMessageBox.information(self, "Info", "Stop command sent to bot.")

def run_window(app_logic):
    qt_app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app_logic)
    window.show()
    qt_app.exec_()

if __name__ == "__main__":
    app_logic = MusicBotApp()
    window_thread = threading.Thread(target=run_window, args=(app_logic,), daemon=True)
    window_thread.start()
    app_logic.run()
