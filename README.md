# Antikorrupsiya Klub Bot

Telegram bot for the Antikorrupsiya klubi (@antikorrupsiyaklub_bot). A student registers
with first and last name, joins the club's Telegram group, has membership verified through the
Telegram Bot API, and receives a personalized PNG congratulation card.

- Python 3.12+, aiogram 3 (long polling), Pillow, Docker Compose
- No database, no web server, no public ports, no webhooks
- Registration state lives only in memory (`MemoryStorage`) and is lost on restart by design

## Project layout

```
app/
  main.py                  entry point, polling, graceful shutdown
  config.py                environment-based settings
  handlers/                start, registration, membership, admin
  keyboards/inline.py      inline keyboards
  states/registration.py   FSM states
  services/certificate.py  PNG rendering (Pillow, in memory)
  services/telegram_membership.py  getChatMember checks
  utils/                   name validation, rate limiting
assets/fonts/              DejaVu fonts (see assets/fonts/LICENSE-DejaVu.txt)
assets/logo/               optional user-provided club logo (not included)
tests/                     pytest suite with mocked Telegram API
```

## Configuration

Copy `.env.example` to `.env` and fill it in. Never commit `.env`.

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | yes | Token from @BotFather |
| `GROUP_ID` | yes | Numeric id of the club group (e.g. `-1001234567890`) |
| `GROUP_INVITE_URL` | yes | `https://` invite link shown to students |
| `ADMIN_TELEGRAM_IDS` | no | Comma-separated numeric Telegram user IDs allowed to use `/admin` |
| `CLUB_LOGO_PATH` | no | Path to a club logo PNG inside the container; omit to render without a logo |
| `TZ` | no | Timezone for the container (default `Asia/Tashkent`) |

The bot **must be an administrator** of the group so `getChatMember` works.

## Running on the server (Debian, Docker Compose)

```bash
cp .env.example .env          # then edit the values
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=100
docker compose down           # graceful stop (SIGTERM, 20s grace period)
```

Only **one** polling instance may run per bot token. Do not start a second copy on another host.

The compose file runs the bot as a non-root user with a read-only root filesystem, dropped
capabilities, CPU/RAM limits (0.5 CPU, 256 MB) and rotated JSON logs (10 MB × 3).

## Admin menu

Send `/admin` from an account whose numeric ID is in `ADMIN_TELEGRAM_IDS`. Non-admins receive
no response. The menu offers:

- **Bot holati** – bot username, polling mode, whether the bot is admin in the group
- **Guruh ma’lumoti** – group title, type and member count
- **Tabriknoma sinovi** – renders a sample card with a placeholder name

The bot keeps no student lists or statistics, so none are shown.

## Privacy

- Names are validated, used to render the card, and kept only in memory for the session.
- Nothing is written to disk; generated PNGs are kept in memory and discarded after sending.
- Names are not written to logs.
- No phone numbers or other personal data are requested. `/privacy` shows the notice to users.
- The bot cannot prove a certificate was issued earlier; it always re-checks membership first.

## Tests and lint

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest -q
```

The tests mock all Telegram API calls. They do not contact Telegram.
