import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_websocket_mock_streams_transcript(auth_token):
    with client.websocket_connect("/ws/listen") as ws:
        ws.send_json({"type": "start", "lang": "hi", "code": "",
                      "device_id": "t1", "token": auth_token})
        types = set()
        for _ in range(3):
            raw = ws.receive_text()
            types.add(json.loads(raw).get("type"))
            if "analysis" in types:
                break
        assert "transcript" in types or "analysis" in types
        ws.send_json({"type": "stop"})


def test_websocket_rejects_bad_start():
    with client.websocket_connect("/ws/listen") as ws:
        ws.send_json({"type": "wrong"})
        raw = ws.receive_text()
        assert json.loads(raw).get("type") == "error"


def test_websocket_requires_token():
    with client.websocket_connect("/ws/listen") as ws:
        ws.send_json({"type": "start", "lang": "hi", "code": "", "device_id": "t2"})
        raw = ws.receive_text()
        assert json.loads(raw).get("code") == "auth_required"
