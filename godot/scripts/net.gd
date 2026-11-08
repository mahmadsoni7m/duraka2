extends Node
signal logged_in
signal message(data: Dictionary)
var http_base := "http://10.0.2.2:8000"   # Android emulator -> host; set your wss:// server for release
var ws_base := "ws://10.0.2.2:8000"
var token := ""
var ws := WebSocketPeer.new()
var _connected := false

func guest_login() -> void:
	var req := HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(_r, code, _h, body):
		if code == 200:
			var d = JSON.parse_string(body.get_string_from_utf8())
			token = d["token"]
			logged_in.emit()
		req.queue_free())
	req.request(http_base + "/auth/guest", ["Content-Type: application/json"], HTTPClient.METHOD_POST, "{}")

func join(code: String) -> void:
	ws = WebSocketPeer.new()
	ws.connect_to_url("%s/ws/%s?token=%s" % [ws_base, code, token])
	_connected = true

func send(d: Dictionary) -> void:
	if ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		ws.send_text(JSON.stringify(d))

func _process(_dt: float) -> void:
	if not _connected:
		return
	ws.poll()
	while ws.get_ready_state() == WebSocketPeer.STATE_OPEN and ws.get_available_packet_count() > 0:
		var d = JSON.parse_string(ws.get_packet().get_string_from_utf8())
		if d is Dictionary:
			message.emit(d)
