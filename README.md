# Steam League Bot

A Discord bot for running a competitive league around a Steam game. Players link their Steam account, get a profile with live playtime, and climb a goals leaderboard managed by admins.

## Features

- `/registrace` links a Steam account to a Discord user
- `/player` shows a profile: Steam name, hours played, team, goals and bio
- `/zebricek` shows the leaderboard ranked by goals
- Admin command group `/admin`:
  - `set-team` assigns a player to a team
  - `set-bio` sets a player bio
  - `add-goly` adds goals to a player
- Optional admin role restriction
- SQLite storage, no external database needed

## Tech Stack

- Python 3.10+
- py-cord
- SQLite
- Steam Web API (requests)

## Getting Started

### Prerequisites

- Python 3.10+
- Discord bot token with the **Server Members** intent enabled
- Steam Web API key (https://steamcommunity.com/dev/apikey)

### Installation

```bash
git clone https://github.com/Exo-Studios-Code/steam-league-bot.git
cd steam-league-bot
pip install -r requirements.txt
```

### Configuration

Copy the example config and fill it in:

```bash
cp config.example.py config.py
```

```python
DISCORD_TOKEN = "your_discord_bot_token"
STEAM_API_KEY = "your_steam_api_key"
STEAM_APP_ID = 2994020      # Steam App ID of your game
ADMIN_ROLE_ID = 0           # 0 = no role check, otherwise your admin role ID
```

### Run

```bash
python bot3.py
```

The `liga.db` database is created automatically on first start.
