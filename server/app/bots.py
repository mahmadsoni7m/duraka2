"""AI bots. They only see Game.view(p) (own hand + public info), never hidden cards."""
import random


def _cost(card, trump):
    return (card[1] == trump, card[0])


def to_move(m):
    return tuple(tuple(x) if isinstance(x, list) else x for x in m)


def choose(view, level="medium", rng=random):
    legal = [to_move(m) for m in view["legal"]]
    if not legal:
        return None
    trump = view["trump"]
    if level == "easy":
        return rng.choice(legal)
    defs = [m for m in legal if m[0] == "defend"]
    if defs:
        best = min(defs, key=lambda m: _cost(m[2], trump))
        if level == "hard" and best[2][1] == trump and best[2][0] >= 11 \
                and view["deck"] > 6 and ("take",) in legal:
            return ("take",)
        return best
    trf = [m for m in legal if m[0] == "transfer"]
    if trf and level == "hard":
        return min(trf, key=lambda m: _cost(m[1], trump))
    atk = [m for m in legal if m[0] == "attack"]
    if atk:
        best = min(atk, key=lambda m: _cost(m[1], trump))
        if view["table"] and best[1][1] == trump and view["deck"] > 0 and ("pass",) in legal:
            return ("pass",)
        return best
    if ("take",) in legal:
        return ("take",)
    return ("pass",) if ("pass",) in legal else legal[0]
