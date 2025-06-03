import logging
import logging.handlers
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
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(
            filename="leatest.log",
            encoding="utf-8",
            maxBytes=1024 * 1024 * self.conf['log_file_size_mb'],
            backupCount=self.conf['log_backup_count'],
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt=self.conf['datefmt']
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def stop_bot(self):
        print("Stopping bot...")

        async def shutdown():
            try:
                await bot.bot.close()
                await asyncio.sleep(0.5)
                pending = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task(self.loop)]
                if pending:
                    print(f"Waiting for {len(pending)} tasks...")
                    await asyncio.gather(*pending, return_exceptions=True)
            except Exception as e:
                print(f"Exception in shutdown: {e}")
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
                else:
                    print(f"Unknown command: {cmd}. Enter help to list the commands.")
        except KeyboardInterrupt:
            print("\nConsole thread exiting.")

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
            print("Event loop closed.")

class MainWindow(QtWidgets.QWidget):
    def __init__(self, app_logic):
        super().__init__()
        self.app_logic = app_logic
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Music Bot Control")
        self.setGeometry(100, 100, 300, 100)
        self.button = QtWidgets.QPushButton("Stop Bot", self)
        self.button.clicked.connect(self.on_stop)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.button)
        self.setLayout(layout)

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
