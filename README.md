# DURAKA — SONI GAMES (stage 1)

Godot 4 (GDScript) Android client + FastAPI authoritative server. Virtual currency (SONI COINS) only.

## Status (honest)
| Area | State |
|---|---|
| Rule engine (36 cards, podkidnoy, perevodnoy, team 2v2, throw-in, transfer, pickup, replenish, end-game) | Done, 33 tests pass (run locally) |
| Bots easy/medium/hard (see only own view) | Done (hard = heuristics, no real card counting yet) |
| Wallet, idempotent rewards, shop buy/equip | Done in memory + tests |
| FastAPI REST + WebSocket rooms, bots fill seats, reconnect grace, server-side rewards | Written, NOT run here (FastAPI not installable in the build sandbox) |
| Godot client: language switch, mode menu, procedurally drawn card table, play vs bots | Written, NOT opened in Godot, APK NOT built |
| PostgreSQL | Schema in server/migrations; server still uses memory (stage 2) |
| Matchmaking, friends, rankings, missions, tournaments, chat, sounds, shop UI, avatars | Not done (stage 2+) |
| GitHub Actions APK | Written, unverified until you push and run it |

## Run server
    cd server && pip install -r requirements.txt
    SONI_DEV=1 SONI_SECRET=x uvicorn app.main:app --host 0.0.0.0 --port 8000
    SONI_DEV=1 python -m pytest -q
Production: set SONI_SECRET in the environment (see .env.example), use wss:// behind a TLS proxy.

## Build APK
Push to GitHub, open Actions -> "Build Android APK" -> download the artifact.
Edit `http_base`/`ws_base` in godot/scripts/net.gd to your server. Add a Cyrillic font (Noto Sans) for Tajik letters.

## Team rules
Seats 1&3 vs 2&4. Attack/defence skips teammates; teammates of the attacker may throw in; a defender's teammate may not.
A team wins when both its players are out of cards (deck empty). One finished teammate does not end the match.
