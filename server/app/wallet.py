"""SONI COINS: virtual currency only. Idempotent, server-side ledger."""
import threading


class WalletError(Exception):
    pass


class Wallet:
    def __init__(self):
        self.balances, self.ledger, self.keys = {}, [], set()
        self.inventory, self.equipped = {}, {}
        self._lock = threading.Lock()

    def balance(self, uid):
        return self.balances.get(uid, 0)

    def _tx(self, uid, amount, reason, key):
        if key in self.keys:
            return False  # duplicate request ignored
        if self.balance(uid) + amount < 0:
            raise WalletError("insufficient coins")
        self.keys.add(key)
        self.balances[uid] = self.balance(uid) + amount
        self.ledger.append({"uid": uid, "amount": amount, "reason": reason, "key": key})
        return True

    def credit(self, uid, amount, reason, key):
        if amount <= 0:
            raise WalletError("bad amount")
        with self._lock:
            return self._tx(uid, amount, reason, key)

    def daily_bonus(self, uid, day, amount=50):
        return self.credit(uid, amount, "daily", f"daily:{uid}:{day}")

    def match_reward(self, uid, match_id, won, finished_on_server):
        if not finished_on_server:
            raise WalletError("match not verified by server")
        return self.credit(uid, 10 + (25 if won else 0), "match", f"match:{match_id}:{uid}")

    def buy(self, uid, item_id, catalog):
        item = catalog.get(item_id)
        if not item:
            raise WalletError("unknown item")
        with self._lock:
            if item_id in self.inventory.setdefault(uid, set()):
                raise WalletError("already owned")
            self._tx(uid, -item["price"], f"buy:{item_id}", f"buy:{uid}:{item_id}")
            self.inventory[uid].add(item_id)

    def equip(self, uid, item_id, catalog):
        if item_id not in self.inventory.get(uid, set()):
            raise WalletError("not owned")
        self.equipped.setdefault(uid, {})[catalog[item_id]["category"]] = item_id


CATALOG = {
    "back_red": {"category": "card_back", "price": 100},
    "back_blue": {"category": "card_back", "price": 100},
    "table_wood": {"category": "table", "price": 250},
    "hat_telpak": {"category": "hat", "price": 150},
    "frame_gold": {"category": "frame", "price": 300},
    "avatar_old_man": {"category": "avatar", "price": 120},
}
