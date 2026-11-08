"""DURAKA SONI GAMES server: FastAPI REST + WebSocket, authoritative game rooms.
Stage 1 keeps state in memory; PostgreSQL schema is in ../migrations (wire-up = stage 2)."""
import asyncio, hashlib, hmac, json, os, random, secrets, string, time, uuid
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from .engine import Game, IllegalMove, make_rules
from .bots import choose, to_move
from .wallet import Wallet, WalletError, CATALOG

SECRET = os.environ.get("SONI_SECRET", "")
if not SECRET:
    if os.environ.get("SONI_DEV") == "1":
        SECRET = "dev-only-secret"
    else:
        raise RuntimeError("SONI_SECRET is required (set SONI_DEV=1 for local dev)")

app = FastAPI(title="DURAKA SONI GAMES")
wallet = Wallet()
users = {}          # uid -> {name, pw_hash(optional)}
by_name = {}
rooms = {}          # code -> Room
_rate = {}
SEATS = {"1v1": 2, "ffa": 4, "team": 4}


def sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(uid):
    p = f"{uid}.{int(time.time()) + 7 * 86400}"
    return f"{p}.{sign(p)}"


def verify(token):
    try:
        uid, exp, sig = token.rsplit(".", 2)
        if hmac.compare_digest(sig, sign(f"{uid}.{exp}")) and int(exp) > time.time() and uid in users:
            return uid
    except Exception:
        pass
    return None


def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()


def limited(key, limit=30, per=60):
    now = time.time()
    hits = [t for t in _rate.get(key, []) if now - t < per]
    hits.append(now); _rate[key] = hits
    return len(hits) > limit


def auth(request: Request):
    if limited(request.client.host if request.client else "x"):
        raise HTTPException(429, "rate limit")
    h = request.headers.get("authorization", "")
    uid = verify(h.removeprefix("Bearer ").strip())
    if not uid:
        raise HTTPException(401, "bad token")
    return uid


@app.post("/auth/guest")
async def guest():
    uid = uuid.uuid4().hex[:12]
    users[uid] = {"name": "Player" + uid[:4]}
    wallet.credit(uid, 100, "welcome", f"welcome:{uid}")
    return {"uid": uid, "token": make_token(uid), "name": users[uid]["name"]}


@app.post("/auth/register")
async def register(body: dict, request: Request):
    if limited("reg:" + (request.client.host if request.client else "x"), 10):
        raise HTTPException(429, "rate limit")
    name, pw = str(body.get("username", ""))[:20].strip(), str(body.get("password", ""))
    if len(name) < 3 or len(pw) < 8 or name in by_name:
        raise HTTPException(400, "invalid or taken")
    uid = uuid.uuid4().hex[:12]
    users[uid] = {"name": name, "pw": hash_pw(pw)}; by_name[name] = uid
    wallet.credit(uid, 100, "welcome", f"welcome:{uid}")
    return {"uid": uid, "token": make_token(uid), "name": name}


@app.post("/auth/login")
async def login(body: dict, request: Request):
    if limited("login:" + (request.client.host if request.client else "x"), 10):
        raise HTTPException(429, "rate limit")
    uid = by_name.get(str(body.get("username", "")))
    if uid:
        salt = users[uid]["pw"].split("$")[0]
        if hmac.compare_digest(users[uid]["pw"], hash_pw(str(body.get("password", "")), salt)):
            return {"uid": uid, "token": make_token(uid), "name": users[uid]["name"]}
    raise HTTPException(401, "bad credentials")


@app.get("/wallet")
async def get_wallet(request: Request):
    uid = auth(request)
    return {"coins": wallet.balance(uid), "history": wallet.ledger[-50:] and
            [t for t in wallet.ledger if t["uid"] == uid][-50:]}


@app.post("/wallet/daily")
async def daily(request: Request):
    uid = auth(request)
    ok = wallet.daily_bonus(uid, time.strftime("%Y-%m-%d", time.gmtime()))
    return {"granted": ok, "coins": wallet.balance(uid)}


@app.get("/shop")
async def shop(request: Request):
    uid = auth(request)
    return {"items": CATALOG, "owned": sorted(wallet.inventory.get(uid, [])),
            "equipped": wallet.equipped.get(uid, {})}


@app.post("/shop/buy")
async def buy(body: dict, request: Request):
    uid = auth(request)
    try:
        wallet.buy(uid, str(body.get("item")), CATALOG)
    except WalletError as e:
        raise HTTPException(400, str(e))
    return {"coins": wallet.balance(uid)}


@app.post("/shop/equip")
async def equip(body: dict, request: Request):
    uid = auth(request)
    try:
        wallet.equip(uid, str(body.get("item")), CATALOG)
    except (WalletError, KeyError) as e:
        raise HTTPException(400, str(e))
    return {"equipped": wallet.equipped[uid]}


class Room:
    def __init__(self, code):
        self.code, self.host = code, None
        self.players = []        # seat -> {"uid","name","bot"}
        self.sockets = {}        # uid -> ws
        self.game, self.mode, self.match_id, self.rewarded = None, None, None, False
        self.lock = asyncio.Lock()

    def seat_of(self, uid):
        return next((i for i, p in enumerate(self.players) if p["uid"] == uid), None)

    async def broadcast(self):
        if not self.game:
            return
        for uid, ws in list(self.sockets.items()):
            s = self.seat_of(uid)
            if s is not None:
                try:
                    await ws.send_json({"t": "state", "view": self.game.view(s),
                                        "names": [p["name"] for p in self.players]})
                except Exception:
                    self.sockets.pop(uid, None)

    async def bots(self):
        for _ in range(500):
            g = self.game
            if g.finished:
                return self.finish()
            acted = False
            for s, p in enumerate(self.players):
                if p["bot"] and g.legal_moves(s):
                    m = choose(g.view(s), p["bot"])
                    await asyncio.sleep(0.6)
                    g.apply(s, to_move(m)); acted = True
                    await self.broadcast(); break
            if not acted:
                return

    def finish(self):
        if self.rewarded or not self.game.finished:
            return
        self.rewarded = True
        winners = set(self.game.result["winners"])
        for s, p in enumerate(self.players):
            if not p["bot"]:
                wallet.match_reward(p["uid"], self.match_id, s in winners, True)


@app.websocket("/ws/{code}")
async def ws_room(ws: WebSocket, code: str, token: str = ""):
    uid = verify(token)
    if not uid or not (3 <= len(code) <= 8) or not code.isalnum():
        await ws.close(code=4401); return
    await ws.accept()
    room = rooms.setdefault(code.upper(), Room(code.upper()))
    if room.host is None:
        room.host = uid
    if room.game is None and room.seat_of(uid) is None and len(room.players) < 4:
        room.players.append({"uid": uid, "name": users[uid]["name"], "bot": None})
    room.sockets[uid] = ws                       # reconnection: same uid reattaches
    await ws.send_json({"t": "joined", "code": room.code, "host": room.host == uid})
    await room.broadcast()
    try:
        while True:
            msg = await ws.receive_json()
            if limited(f"ws:{uid}", 120, 10):
                continue
            async with room.lock:
                try:
                    if msg.get("t") == "start" and uid == room.host and room.game is None:
                        mode = msg.get("mode", "1v1")
                        if mode not in SEATS:
                            raise IllegalMove("mode")
                        n = SEATS[mode]
                        lvl = msg.get("bots", "medium")
                        if lvl not in ("easy", "medium", "hard"):
                            lvl = "medium"
                        humans = room.players[:n]
                        while len(humans) < n:
                            humans.append({"uid": "bot%d" % len(humans), "name": "Bot %d" % len(humans), "bot": lvl})
                        room.players, room.mode = humans, mode
                        room.match_id = uuid.uuid4().hex
                        room.game = Game(n, make_rules(mode, msg.get("variant", "podkidnoy")))
                        await room.broadcast()
                        asyncio.create_task(room.bots())
                    elif msg.get("t") == "move" and room.game:
                        s = room.seat_of(uid)
                        if s is None:
                            raise IllegalMove("spectator")
                        room.game.apply(s, to_move(msg["m"]))
                        await room.broadcast()
                        asyncio.create_task(room.bots())
                except (IllegalMove, KeyError, TypeError, ValueError) as e:
                    await ws.send_json({"t": "error", "msg": str(e)})
    except WebSocketDisconnect:
        room.sockets.pop(uid, None)
        s = room.seat_of(uid)
        if room.game and s is not None and not room.game.finished:
            await asyncio.sleep(30)               # grace period for reconnect
            if uid not in room.sockets and not room.game.finished:
                async with room.lock:
                    room.game.force_timeout(s)
                    await room.broadcast()
                    asyncio.create_task(room.bots())
