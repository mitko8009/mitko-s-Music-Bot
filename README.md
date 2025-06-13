# Mitko's Music Bot

## Overview

Mitko's Music Bot is a Discord bot designed for seamless music playback in your server. It features both a graphical user interface *(GUI)* and console commands for easier management and control.

## Features

- 🎵 Play music directly in Discord voice channels.
- 🎛️ GUI for managing the bot.
- 💻 Console commands for advanced control and debugging.
- 🔎 Search and queue songs.
- ⏯️ Pause, resume, skip, and stop playback.
- 📃 Display the current playlist queue.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/mitko8009/mitkos-Music-Bot.git
    ```
2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Set up your Discord bot token in an environment variable or configuration file as needed.

4. Run the bot:
    ```bash
    python main.py
    ```

## Usage

- Command-line arguments
  - `--gui` — open the GUI on startup.
  - `debug` — enable debugging mode.
- Console commands:
  - `clear` — clear the console.
  - `stop` — shut down the bot.
  - `gui` — open the control GUI.
- GUI options
  - Click on `Manage` (top left corner), then select `Enable Debug` to activate debug mode from the GUI.
  - Right-click on any cell of the guild's row you want to manage for more options (e.g. **Disconnect**, **Skip Song**, etc.).


## Requirements

- Python 3.x
- Discord API token
- Internet connection for streaming music

## Contributing

Feel free to fork the repository and submit pull requests. Contributions, feature requests, and bug reports are welcome!
