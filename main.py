import logging
import logging.handlers
import colorlog
import json
import threading
import asyncio
import time
import sys
import gc
import os

from PyQt5 import QtCore, QtWidgets, uic

import bot

class MusicBotApp:
    def __init__(self):
        self.conf = json.loads(open("config.json", 'r').read())
        if "debug" in sys.argv: self.conf['debug'] = True
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
                    "DEBUG": self.conf['logging']['asctime_log_color'],
                    "INFO": self.conf['logging']['asctime_log_color'],
                    "WARNING": self.conf['logging']['asctime_log_color'],
                    "ERROR": self.conf['logging']['asctime_log_color'],
                    "CRITICAL": self.conf['logging']['asctime_log_color'],
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
                cmd = input("").strip().lower()
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
                
                elif cmd == "gui":
                    if is_gui_open():
                        self.logger.warning("GUI is already open.")
                    else:
                        self.logger.info("Opening GUI...")
                        window_thread = threading.Thread(target=run_window, args=(self,), daemon=True)
                        window_thread.start()

                elif cmd == "clear":
                    if sys.platform == "win32":
                        _ = os.system('cls')
                    else:
                        _ = os.system('clear')

                else:
                    print(f"\033[93mUnknown command: \033[91m{cmd}\033[0m")
        except KeyboardInterrupt:
            self.logger.info("Console interrupted by user.")

    def run(self) -> None:
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

    
    def check_bot_status(self) -> str:
        if bot.bot.is_closed(): return "offline"
        elif not bot.is_ready: return "starting"
        else: return "online"

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app_logic):
        while not bot.is_ready:
            time.sleep(0.1)

        super().__init__()
        self.app_logic = app_logic

        uic.loadUi("ui/main.ui", self)
        self.functionality()

    def functionality(self):
        self.setWindowTitle(f"Discord Bot Control Panel - {bot.bot.user.name}")

        self.is_debug = self.app_logic.conf['debug']

        self.stop_btn.clicked.connect(self.on_stop)
        self.actionShutdown.triggered.connect(self.on_stop)
        self.actionEnable_Debug.setChecked(self.is_debug)
        self.actionEnable_Debug.triggered.connect(self.toggle_debug)
        self.label_bot_details.setText(f"Logged in as {bot.bot.user} (ID: {bot.bot.user.id})")

        # Activity Table
        HeaderLabels = ["Guild Name", "Status"]
        self.table_activity.setColumnCount(len(HeaderLabels))
        self.table_activity.setHorizontalHeaderLabels(HeaderLabels)
        self.refresh_activity_table()

        # Refresh activity table
        self.activity_timer = QtCore.QTimer(self)
        self.activity_timer.timeout.connect(self.refresh_activity_table)
        self.activity_timer.start(3000)

        # Add right-click context menu
        self.table_activity.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_activity.customContextMenuRequested.connect(self.show_activity_context_menu)

    def refresh_activity_table(self):
        self.label_status.setText(self.app_logic.check_bot_status().upper())
        if self.app_logic.check_bot_status() == 'online': self.label_status.setStyleSheet("color: green;")
        else: self.label_status.setStyleSheet("color: red;")
        
        self.table_activity.setRowCount(0)
        for guild in bot.bot.guilds:
            row = self.table_activity.rowCount()
            self.table_activity.insertRow(row)

            # Guild Name
            item = QtWidgets.QTableWidgetItem(guild.name)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table_activity.setItem(row, 0, item)

            # Voice Status
            voice_client = next((vc for vc in bot.bot.voice_clients if vc.guild.id == guild.id and vc.is_connected()), None)
            if voice_client and voice_client.channel:
                status_text = f"Active ({voice_client.channel.name})"
            else:
                status_text = "Inactive"
            status_item = QtWidgets.QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table_activity.setItem(row, 1, status_item)

    def show_activity_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        action_refresh = menu.addAction("Refresh Table Info")
        menu.addSeparator()
        action_copy_id = menu.addAction("Copy Guild ID")
        action_skip_song = menu.addAction("Skip Song")
        action_disconnect = menu.addAction("Disconnect from Guild")
        action = menu.exec_(self.table_activity.viewport().mapToGlobal(pos))

        # Refresh the activity table
        if action == action_refresh:
            self.refresh_activity_table()
        
        # Copy the guild ID to clipboard
        elif action == action_copy_id:
            row = self.table_activity.currentRow()
            if row >= 0 and row < len(bot.bot.guilds):
                guild_id = str(bot.bot.guilds[row].id)
                QtWidgets.QApplication.clipboard().setText(guild_id)

        # Disconnect from the voice channel
        elif action == action_disconnect:
            row = self.table_activity.currentRow()
            if row >= 0 and row < len(bot.bot.guilds):
                guild = bot.bot.guilds[row]
                voice_client = next((vc for vc in bot.bot.voice_clients if vc.guild.id == guild.id and vc.is_connected()), None)
                if voice_client:
                    # Disconnect asynchronously
                    def disconnect():
                        fut = asyncio.run_coroutine_threadsafe(voice_client.disconnect(), self.app_logic.loop)
                        try:
                            fut.result(timeout=5)
                        except Exception as e:
                            self.app_logic.logger.error(f"Failed to disconnect from {guild.name}: {e}")
                    threading.Thread(target=disconnect, daemon=True).start()
                    self.app_logic.logger.info(f"Disconnect command sent for guild: {guild.name}")
                else:
                    self.app_logic.logger.warning(f"Bot is not connected to a voice channel in guild: {guild.name}")

        # Skip song in the selected guild
        elif action == action_skip_song:
            row = self.table_activity.currentRow()
            if row >= 0 and row < len(bot.bot.guilds):
                guild = bot.bot.guilds[row]
                def skip():
                    fut = asyncio.run_coroutine_threadsafe(
                        bot.skip_song(guild.id), self.app_logic.loop
                    )
                    try:
                        fut.result(timeout=5)
                        self.app_logic.logger.info(f"Skip command sent for guild: {guild.name}")
                    except Exception as e:
                        self.app_logic.logger.error(f"Failed to skip song in {guild.name}: {e}")
                threading.Thread(target=skip, daemon=True).start()
            else:
                self.app_logic.logger.warning("No guild selected to skip song.")
        
    def update_stats(self):
        if self.app_logic.check_bot_status() != 'online': return
        pass

    def toggle_debug(self):
        is_checked = self.actionEnable_Debug.isChecked()
        self.app_logic.conf['debug'] = is_checked
        self.app_logic.logger.setLevel(logging.DEBUG if is_checked else logging.INFO)
        self.app_logic.logger.info("Debug mode enabled." if is_checked else "Debug mode disabled.")


    def on_stop(self):
        if self.app_logic.check_bot_status() != "online":
            self.app_logic.logger.warning("Bot is not running. No action taken.")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Stop",
            "Are you sure you want to stop the bot?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.app_logic.stop_bot()
            QtWidgets.QMessageBox.information(self, "Info", "Stop command sent to bot.")

def run_window(app_logic):
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow(app_logic)
        window.show()
        app.exec_()
    else:
        window = MainWindow(app_logic)
        window.show()


def is_gui_open() -> bool:
    return QtWidgets.QApplication.instance() is not None

if __name__ == "__main__":
    app_logic = MusicBotApp()

    if "--gui" in sys.argv: # GUI mode
        window_thread = threading.Thread(target=run_window, args=(app_logic,), daemon=True)
        window_thread.start()
    
    app_logic.run()
