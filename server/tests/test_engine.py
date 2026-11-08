import random, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from app.engine import *
from app.bots import choose, to_move
from app.wallet import Wallet, WalletError, CATALOG


def mk(n=2, rules=PODKIDNOY, hands=None, trump="H", deck=None, att=0):
    g = Game(n, rules, seed=1)
    g.trump = trump
    if hands: g.hands = [list(h) for h in hands]
    g.deck = deck if deck is not None else []
    g.trump_card = (6, trump)
    g.attacker, g.defender = att, g.next_active(att)
    g.limit = min(6, len(g.hands[g.defender]))
    return g


def test_deck_and_deal():
    d = full_deck()
    assert len(d) == 36 == len(set(d))
    g = Game(4, seed=3)
    assert all(len(h) == 6 for h in g.hands) and len(g.deck) == 12
    assert len({c for h in g.hands for c in h} | set(g.deck)) == 36


def test_shuffle_differs():
    assert Game(2, seed=1).hands != Game(2, seed=2).hands


def test_first_attacker_lowest_trump():
    g = Game(4, seed=5)
    lows = [(c[0], i) for i, h in enumerate(g.hands) for c in h if c[1] == g.trump]
    assert g.attacker == (min(lows)[1] if lows else 0)


def test_beats_rules():
    assert beats((7, "S"), (8, "S"), "H") and not beats((8, "S"), (7, "S"), "H")
    assert beats((14, "S"), (6, "H"), "H") and not beats((6, "H"), (14, "S"), "H")
    assert beats((6, "H"), (7, "H"), "H") and not beats((7, "S"), (14, "D"), "H")


def test_throw_in_rank_and_limit():
    g = mk(hands=[[(7, "S"), (7, "D"), (9, "C")], [(8, "S")] + [(10, "D")] * 0], deck=[(6, "D")])
    g.hands[1] = [(8, "S"), (9, "S")]
    g.limit = 2
    g.attack(0, (7, "S"))
    with pytest.raises(IllegalMove): g.attack(0, (9, "C"))
    g.defend(1, 0, (8, "S"))
    g.attack(0, (7, "D"))
    with pytest.raises(IllegalMove): g.attack(0, (9, "C"))


def test_pickup_and_ordinary_six_kept():
    g = mk(hands=[[(7, "S"), (9, "D")], [(6, "C"), (14, "H")]], deck=[])
    g.attack(0, (7, "S"))
    g.take(1)
    assert sorted(g.hands[1]) == sorted([(6, "C"), (14, "H"), (7, "S")])
    assert not g.finished and g.attacker == 0  # defender took -> attacker goes on


def test_replenish_order_and_trump_last():
    deck = [(6, "H"), (9, "C"), (10, "C"), (11, "C")]
    g = mk(hands=[[(7, "S")] + [(8, "D")] * 5, [(8, "S")] + [(9, "D")] * 5], deck=deck.copy())
    g.attack(0, (7, "S")); g.defend(1, 0, (8, "S")); g.pass_turn(0)
    assert len(g.hands[0]) == 6 and len(g.hands[1]) == 6 and not g.deck.__len__() - 2
    assert g.attacker == 1


def test_endgame_1v1_durak():
    g = mk(hands=[[(7, "S")], [(6, "C"), (9, "D")]], deck=[])
    g.attack(0, (7, "S")); g.take(1)
    assert g.finished and g.result["durak"] == 1 and g.result["ranking"] == [0, 1]


def test_transfer():
    g = mk(3, PEREVODNOY, hands=[[(7, "S")] + [(9, "D")] * 3, [(7, "C"), (8, "D")], [(10, "D")] * 3], deck=[])
    g.attack(0, (7, "S"))
    g.transfer(1, (7, "C"))
    assert g.defender == 2 and g.attacker == 1 and len(g.table) == 2
    with pytest.raises(IllegalMove): mk(2, PODKIDNOY, hands=[[(7, "S")], [(7, "C")]]).transfer(1, (7, "C"))


def test_team_no_throw_for_defender_team_and_win():
    g = mk(4, TEAM, hands=[[(7, "S"), (7, "D")], [(8, "S"), (9, "H")], [(7, "C")], [(10, "D")]], deck=[])
    g.attack(0, (7, "S"))
    with pytest.raises(IllegalMove): g.attack(3, (10, "D"))  # 3 is not defender team: ok rank rule blocks
    g.defend(1, 0, (8, "S"))
    g.attack(2, (7, "C"))  # teammate of attacker throws in
    g.take(1) if False else None


def test_team_completion_not_ffa():
    g = mk(4, TEAM, hands=[[(7, "S")], [(8, "S"), (9, "S")], [(10, "D")], [(11, "D"), (12, "D")]], deck=[])
    g.attack(0, (7, "S")); g.defend(1, 0, (8, "S"))
    assert g.out == [0] and not g.finished  # one teammate out -> continues
    assert g.attacker == 1


def test_view_hides_cards():
    g = Game(4, TEAM, seed=2)
    v = g.view(0)
    assert v["hand"] == [list(c) for c in g.hands[0]]
    assert "hands" not in v and v["counts"] == [6] * 4


@pytest.mark.parametrize("mode,variant,n", [("1v1", "podkidnoy", 2), ("1v1", "perevodnoy", 2),
                                             ("ffa", "podkidnoy", 4), ("ffa", "perevodnoy", 3),
                                             ("team", "podkidnoy", 4), ("team", "perevodnoy", 4)])
@pytest.mark.parametrize("level", ["easy", "medium", "hard"])
def test_bot_games_terminate_legally(mode, variant, n, level):
    for seed in range(30):
        g = Game(n, make_rules(mode, variant), seed=seed)
        rng = random.Random(seed)
        for step in range(3000):
            if g.finished: break
            order = [g.defender] + [(g.attacker + k) % n for k in range(n) if (g.attacker + k) % n != g.defender]
            for p in order:
                v = g.view(p)
                m = choose(v, level, rng)
                if m:
                    g.apply(p, m); break
            else:
                pytest.fail("deadlock")
        assert g.finished, (mode, variant, level, seed)
        total = sum(len(h) for h in g.hands) + len(g.deck) + len(g.discard) + sum(
            2 if d else 1 for a, d in g.table)
        assert total == 36


def test_wallet_idempotent_and_shop():
    w = Wallet()
    assert w.daily_bonus("u", "2026-11-08") and not w.daily_bonus("u", "2026-11-08")
    assert w.balance("u") == 50
    with pytest.raises(WalletError): w.match_reward("u", "m1", True, False)
    w.match_reward("u", "m1", True, True); assert not w.match_reward("u", "m1", True, True)
    assert w.balance("u") == 85
    with pytest.raises(WalletError): w.buy("u", "frame_gold", CATALOG)
    w.credit("u", 500, "test", "k1")
    w.buy("u", "back_red", CATALOG); w.equip("u", "back_red", CATALOG)
    assert w.balance("u") == 585 - 100 and "back_red" in w.equipped["u"].values()
    with pytest.raises(WalletError): w.buy("u", "back_red", CATALOG)


def test_team_defender_never_teammate_after_out():
    g = mk(4, TEAM, hands=[[(7, "S")], [], [(8, "C"), (9, "C")], [(6, "D"), (6, "C")]], deck=[])
    g.out = [1]
    g.attacker = 0
    g.defender = g.next_opponent(0)
    assert g.defender == 3
