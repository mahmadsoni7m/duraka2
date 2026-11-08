extends Control
# Procedurally drawn classic card table (no external assets needed).
const SUIT_COL := {"H": Color("c62828"), "D": Color("c62828"), "C": Color("111111"), "S": Color("111111")}
const RANK := {11: "J", 12: "Q", 13: "K", 14: "A"}
var view := {}
var names := []
var menu: VBoxContainer
var hit: Array = []   # [Rect2, card Array]
var status := ""

func _ready() -> void:
	menu = VBoxContainer.new()
	menu.set_anchors_preset(Control.PRESET_CENTER)
	add_child(menu)
	var title := Label.new(); title.text = "DURAKA — SONI GAMES"; menu.add_child(title)
	for lg in ["tg", "ru", "en"]:
		var b := Button.new(); b.text = lg.to_upper()
		b.pressed.connect(func(): Loc.lang = lg; _rebuild_menu())
		menu.add_child(b)
	Net.logged_in.connect(_rebuild_menu)
	Net.message.connect(_on_msg)
	Net.guest_login()

func _rebuild_menu() -> void:
	for c in menu.get_children():
		if c is Button and c.text.length() > 2: c.queue_free()
	for m in [["1v1", "m1v1"], ["ffa", "mffa"], ["team", "mteam"]]:
		for v in ["podkidnoy", "perevodnoy"]:
			var b := Button.new(); b.text = "%s — %s" % [Loc.t(m[1]), Loc.t(v)]
			b.pressed.connect(func(): _start(m[0], v))
			menu.add_child(b)

func _start(mode: String, variant: String) -> void:
	var code := str(randi() % 900000 + 100000)
	Net.join(code)
	await get_tree().create_timer(1.0).timeout
	Net.send({"t": "start", "mode": mode, "variant": variant, "bots": "medium"})
	menu.hide()

func _on_msg(d: Dictionary) -> void:
	if d.get("t") == "state":
		view = d["view"]; names = d["names"]
	elif d.get("t") == "error":
		status = str(d.get("msg"))
	queue_redraw()

func _draw_suit(c: Vector2, s: String, r: float, col: Color) -> void:
	match s:
		"H":
			draw_circle(c + Vector2(-r * .5, -r * .3), r * .55, col)
			draw_circle(c + Vector2(r * .5, -r * .3), r * .55, col)
			draw_colored_polygon(PackedVector2Array([c + Vector2(-r * 1.02, -r * .05), c + Vector2(r * 1.02, -r * .05), c + Vector2(0, r * 1.1)]), col)
		"D":
			draw_colored_polygon(PackedVector2Array([c + Vector2(0, -r * 1.1), c + Vector2(r * .8, 0), c + Vector2(0, r * 1.1), c + Vector2(-r * .8, 0)]), col)
		"C":
			for o in [Vector2(0, -r * .55), Vector2(-r * .6, r * .25), Vector2(r * .6, r * .25)]:
				draw_circle(c + o, r * .5, col)
			draw_rect(Rect2(c + Vector2(-r * .12, 0), Vector2(r * .24, r * 1.1)), col)
		"S":
			draw_circle(c + Vector2(-r * .5, r * .15), r * .55, col)
			draw_circle(c + Vector2(r * .5, r * .15), r * .55, col)
			draw_colored_polygon(PackedVector2Array([c + Vector2(-r * 1.02, r * .0), c + Vector2(r * 1.02, r * .0), c + Vector2(0, -r * 1.15)]), col)
			draw_rect(Rect2(c + Vector2(-r * .12, 0), Vector2(r * .24, r * 1.1)), col)

func _card(pos: Vector2, card, size := Vector2(70, 100), back := false) -> Rect2:
	var rc := Rect2(pos, size)
	draw_rect(Rect2(pos + Vector2(3, 4), size), Color(0, 0, 0, .3))   # shadow
	if back:
		draw_rect(rc, Color("8d1c1c")); draw_rect(rc.grow(-5), Color("f3e9d2"), false, 2)
		return rc
	draw_rect(rc, Color("fdfdf8")); draw_rect(rc, Color("999999"), false, 1)
	var s: String = card[1]; var col: Color = SUIT_COL[s]
	var rk: String = RANK.get(int(card[0]), str(int(card[0])))
	draw_string(ThemeDB.fallback_font, pos + Vector2(6, 20), rk, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, col)
	_draw_suit(pos + size / 2, s, size.x * .22, col)
	return rc

func _draw() -> void:
	var sz := size
	draw_rect(Rect2(Vector2.ZERO, sz), Color("3b2a1a"))
	draw_rect(Rect2(Vector2(20, 20), sz - Vector2(40, 40)), Color("1b6b3f"))
	hit.clear()
	if view.is_empty(): return
	var me: int = view["you"]
	var n: int = view["n"]
	# opponents
	for k in range(1, n):
		var seat := (me + k) % n
		var x := sz.x * (k / float(n)) - 40
		draw_string(ThemeDB.fallback_font, Vector2(x, 50), "%s  [%d]" % [names[seat], view["counts"][seat]], HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color.WHITE)
		_card(Vector2(x, 60), null, Vector2(40, 56), true)
	# deck + trump
	_card(Vector2(40, sz.y / 2 - 50), null, Vector2(70, 100), true)
	if view["trump_card"] != null:
		_card(Vector2(70, sz.y / 2 - 20), view["trump_card"], Vector2(70, 100))
	draw_string(ThemeDB.fallback_font, Vector2(40, sz.y / 2 + 80), "%s: %s  (%d)" % [Loc.t("trump"), view["trump"], view["deck"]], HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color.WHITE)
	# table
	var tbl: Array = view["table"]
	for i in range(tbl.size()):
		var p: Array = tbl[i]
		var x: float = 200.0 + float(i % 6) * 130.0
		var y: float = sz.y / 2.0 - 90.0
		_card(Vector2(x, y), p[0])
		if p[1] != null: _card(Vector2(x + 22, y + 24), p[1])
		else: hit.append([Rect2(Vector2(x, y), Vector2(70, 100)), ["target", i]])
	# hand
	var hand: Array = view["hand"]
	var step: float = min(80.0, (sz.x - 200) / max(1, hand.size()))
	for i in hand.size():
		var pos := Vector2(100 + i * step, sz.y - 130)
		hit.append([_card(pos, hand[i], Vector2(70, 100)), ["card", hand[i]]])
	# state line
	var line := status
	if view["finished"]:
		var r = view["result"]
		var won: bool = (me in r["winners"])
		line = Loc.t("win") if won else Loc.t("lose")
	elif view["defender"] == me: line = "→ %s" % Loc.t("take")
	draw_string(ThemeDB.fallback_font, Vector2(20, sz.y - 10), line, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color("ffd54f"))
	# action buttons
	for mv in view["legal"]:
		if mv[0] == "take": _btn(Rect2(sz.x - 220, sz.y - 70, 90, 50), Loc.t("take"), "take")
		if mv[0] == "pass": _btn(Rect2(sz.x - 120, sz.y - 70, 90, 50), Loc.t("pass"), "pass")

func _btn(r: Rect2, label: String, id: String) -> void:
	draw_rect(r, Color("f3e9d2")); draw_string(ThemeDB.fallback_font, r.position + Vector2(8, 32), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color.BLACK)
	hit.append([r, [id]])

func _gui_input(e: InputEvent) -> void:
	if not (e is InputEventMouseButton and e.pressed) and not (e is InputEventScreenTouch and e.pressed):
		return
	for h in hit:
		if h[0].has_point(e.position):
			_tap(h[1]); return

func _tap(t: Array) -> void:
	if t[0] == "take" or t[0] == "pass":
		Net.send({"t": "move", "m": [t[0]]}); return
	if t[0] == "card":
		var c = t[1]
		for mv in view["legal"]:
			if mv[0] == "defend" and mv[2][0] == c[0] and mv[2][1] == c[1]:
				Net.send({"t": "move", "m": mv}); return
		for mv in view["legal"]:
			if (mv[0] == "attack" or mv[0] == "transfer") and mv[1][0] == c[0] and mv[1][1] == c[1]:
				Net.send({"t": "move", "m": mv}); return
