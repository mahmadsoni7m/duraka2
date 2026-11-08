"""Authoritative Durak engine: 36 cards, podkidnoy / perevodnoy / team (2v2).

Cards are (rank, suit) tuples. rank 6..14 (11=J,12=Q,13=K,14=A), suit in "HDCS".
Seats are clockwise 0..n-1. Team mode: seats 0&2 vs 1&3.
"""
from __future__ import annotations
import random
from dataclasses import dataclass

RANKS = (6, 7, 8, 9, 10, 11, 12, 13, 14)
SUITS = ("H", "D", "C", "S")


class IllegalMove(Exception):
    pass


def full_deck():
    return [(r, s) for s in SUITS for r in RANKS]


def beats(att, dfn, trump):
    """True if dfn legally beats att."""
    if att[1] == dfn[1]:
        return dfn[0] > att[0]
    return dfn[1] == trump


@dataclass(frozen=True)
class Rules:
    name: str
    allow_transfer: bool = False
    team: bool = False


PODKIDNOY = Rules("podkidnoy")
PEREVODNOY = Rules("perevodnoy", allow_transfer=True)
TEAM = Rules("team", team=True)
TEAM_PEREVODNOY = Rules("team_perevodnoy", allow_transfer=True, team=True)


def make_rules(mode: str, variant: str = "podkidnoy") -> Rules:
    transfer = variant == "perevodnoy"
    if mode == "team":
        return TEAM_PEREVODNOY if transfer else TEAM
    return PEREVODNOY if transfer else PODKIDNOY


class Game:
    HAND = 6

    def __init__(self, n: int, rules: Rules = PODKIDNOY, seed=None):
        if n not in (2, 3, 4):
            raise ValueError("2-4 players")
        if rules.team and n != 4:
            raise ValueError("team mode needs 4 players")
        self.n, self.rules = n, rules
        self.rng = random.Random(seed)
        self.deck = full_deck()
        self.rng.shuffle(self.deck)
        self.hands = [[self.deck.pop() for _ in range(self.HAND)] for _ in range(n)]
        self.trump_card = self.deck[0]  # drawn last
        self.trump = self.trump_card[1]
        self.discard = []
        lows = [(c[0], i) for i, h in enumerate(self.hands) for c in h if c[1] == self.trump]
        self.attacker = min(lows)[1] if lows else 0
        self.out, self.finished, self.result = [], False, None
        self.table, self.taking, self.passed = [], False, set()
        self.defender = self.next_opponent(self.attacker)
        self.limit = min(6, len(self.hands[self.defender]))

    # ---------- helpers ----------
    def team_of(self, p):
        return p % 2 if self.rules.team else p

    def next_active(self, i):
        for k in range(1, self.n + 1):
            j = (i + k) % self.n
            if j not in self.out:
                return j
        return i

    def next_opponent(self, i):
        """Next active seat clockwise; in team mode skips teammates of i."""
        for k in range(1, self.n + 1):
            j = (i + k) % self.n
            if j not in self.out and (not self.rules.team or self.team_of(j) != self.team_of(i)):
                return j
        return i

    def _ranks(self):
        return {c[0] for pair in self.table for c in pair if c}

    def _throwers(self):
        seq = [(self.attacker + k) % self.n for k in range(self.n)]
        return [p for p in seq if p not in self.out and self.hands[p]
                and self.team_of(p) != self.team_of(self.defender)]

    def _throw_cards(self, p):
        if not self.table or len(self.table) >= self.limit:
            return []
        r = self._ranks()
        return [c for c in self.hands[p] if c[0] in r]

    def _check_live(self):
        if self.finished:
            raise IllegalMove("game finished")

    # ---------- actions ----------
    def attack(self, p, card):
        self._check_live()
        card = tuple(card)
        if p in self.out or p == self.defender or card not in self.hands[p]:
            raise IllegalMove("cannot attack")
        if self.team_of(p) == self.team_of(self.defender):
            raise IllegalMove("cannot attack own team")
        if not self.table:
            if p != self.attacker:
                raise IllegalMove("not the attacker")
        elif card[0] not in self._ranks():
            raise IllegalMove("rank not on table")
        if len(self.table) >= self.limit:
            raise IllegalMove("attack limit reached")
        self.hands[p].remove(card)
        self.table.append([card, None])
        self.passed.clear()
        self._after()

    def defend(self, p, idx, card):
        self._check_live()
        card = tuple(card)
        if p != self.defender or self.taking or card not in self.hands[p]:
            raise IllegalMove("cannot defend")
        if not (0 <= idx < len(self.table)) or self.table[idx][1] is not None:
            raise IllegalMove("bad target")
        if not beats(self.table[idx][0], card, self.trump):
            raise IllegalMove("card does not beat")
        self.hands[p].remove(card)
        self.table[idx][1] = card
        self._after()

    def _transfer_target(self, p, card):
        r = self.rules
        if not r.allow_transfer or p != self.defender or self.taking or self.finished:
            raise IllegalMove("transfer not allowed")
        if card not in self.hands[p] or not self.table:
            raise IllegalMove("bad card")
        if any(d is not None for _, d in self.table):
            raise IllegalMove("already defended")
        if any(a[0] != card[0] for a, _ in self.table):
            raise IllegalMove("rank mismatch")
        tgt = self.next_opponent(p)
        if tgt == p:
            raise IllegalMove("no valid target")
        if len(self.table) + 1 > min(6, len(self.hands[tgt])):
            raise IllegalMove("target has too few cards")
        return tgt

    def transfer(self, p, card):
        card = tuple(card)
        tgt = self._transfer_target(p, card)
        self.hands[p].remove(card)
        self.table.append([card, None])
        self.attacker, self.defender = p, tgt
        self.limit = min(6, len(self.hands[tgt]))
        self.passed.clear()

    def take(self, p):
        self._check_live()
        if p != self.defender or self.taking or not any(d is None for _, d in self.table):
            raise IllegalMove("cannot take")
        self.taking = True
        self.passed.clear()
        self._after()

    def pass_turn(self, p):
        self._check_live()
        if p not in self._throwers() or not self.table:
            raise IllegalMove("cannot pass")
        if not (self.taking or all(d is not None for _, d in self.table)):
            raise IllegalMove("defence in progress")
        self.passed.add(p)
        self._after()

    def apply(self, p, move):
        k = move[0]
        if k == "attack": self.attack(p, move[1])
        elif k == "defend": self.defend(p, move[1], move[2])
        elif k == "transfer": self.transfer(p, move[1])
        elif k == "take": self.take(p)
        elif k == "pass": self.pass_turn(p)
        else: raise IllegalMove("unknown move")

    def force_timeout(self, p):
        """Disconnect / timeout handling: defender takes, others pass."""
        if self.finished:
            return
        if p == self.defender:
            if not self.taking and any(d is None for _, d in self.table):
                self.take(p)
        elif self.table and p in self._throwers() and (
                self.taking or all(d is not None for _, d in self.table)):
            self.pass_turn(p)
        elif not self.table and p == self.attacker:
            self.attack(p, min(self.hands[p], key=lambda c: (c[1] == self.trump, c[0])))

    # ---------- resolution ----------
    def _after(self):
        if not self.table:
            return
        if not (self.taking or all(d is not None for _, d in self.table)):
            return
        for p in self._throwers():
            if p not in self.passed and self._throw_cards(p):
                return
        self._resolve()

    def _resolve(self):
        att, dfn = self.attacker, self.defender
        cards = [c for pair in self.table for c in pair if c]
        if self.taking:
            self.hands[dfn].extend(cards)
        else:
            self.discard.extend(cards)
        was_taking = self.taking
        self.table, self.taking = [], False
        self.passed.clear()
        seq = [(att + k) % self.n for k in range(self.n)]
        for p in [x for x in seq if x != dfn] + [dfn]:
            if p in self.out:
                continue
            while len(self.hands[p]) < self.HAND and self.deck:
                self.hands[p].append(self.deck.pop())
        for p in seq:
            if p not in self.out and not self.hands[p] and not self.deck:
                self.out.append(p)
        self._check_end()
        if self.finished:
            return
        nxt = dfn if (not was_taking and dfn not in self.out) else self.next_active(dfn)
        self.attacker = nxt
        self.defender = self.next_opponent(nxt)
        self.limit = min(6, len(self.hands[self.defender]))

    def _check_end(self):
        active = [p for p in range(self.n) if p not in self.out]
        if self.rules.team:
            done = {}
            for t in (0, 1):
                members = [p for p in range(self.n) if p % 2 == t]
                if all(m in self.out for m in members):
                    done[t] = max(self.out.index(m) for m in members)
            if done:
                w = min(done, key=done.get)
                self.finished = True
                self.result = {"mode": "team", "winner_team": w,
                               "winners": [p for p in range(self.n) if p % 2 == w],
                               "ranking": self.out + active}
        elif len(active) <= 1:
            self.finished = True
            self.result = {"mode": "ffa", "durak": active[0] if active else None,
                           "winners": list(self.out), "ranking": self.out + active}

    # ---------- queries ----------
    def legal_moves(self, p):
        if self.finished or p in self.out:
            return []
        h, mv = self.hands[p], []
        if p == self.defender:
            if self.taking or not self.table:
                return []
            for i, (a, d) in enumerate(self.table):
                if d is None:
                    mv += [("defend", i, c) for c in h if beats(a, c, self.trump)]
            for c in h:
                try:
                    self._transfer_target(p, c)
                    mv.append(("transfer", c))
                except IllegalMove:
                    pass
            if any(d is None for _, d in self.table):
                mv.append(("take",))
            return mv
        if self.team_of(p) == self.team_of(self.defender):
            return []
        if not self.table:
            return [("attack", c) for c in h] if p == self.attacker else []
        mv += [("attack", c) for c in self._throw_cards(p)]
        if p in self._throwers() and p not in self.passed and (
                self.taking or all(d is not None for _, d in self.table)):
            mv.append(("pass",))
        return mv

    def view(self, p):
        """Per-player view. Never contains other players' hidden cards."""
        return {
            "you": p, "n": self.n, "team": self.rules.team,
            "hand": [list(c) for c in self.hands[p]],
            "counts": [len(h) for h in self.hands],
            "table": [[list(a), list(d) if d else None] for a, d in self.table],
            "trump": self.trump,
            "trump_card": list(self.trump_card) if self.deck else None,
            "deck": len(self.deck), "discard": len(self.discard),
            "attacker": self.attacker, "defender": self.defender,
            "taking": self.taking, "out": list(self.out),
            "finished": self.finished, "result": self.result,
            "legal": [[m[0]] + [list(x) if isinstance(x, tuple) else x for x in m[1:]]
                      for m in self.legal_moves(p)],
        }
