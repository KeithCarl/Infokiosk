import json
from pathlib import Path

from fastapi.testclient import TestClient

import agent.app as app


def test_playlist_requires_auth():
    client = TestClient(app.APP)
    response = client.post("/api/playlist", json=[])
    assert response.status_code in {401, 403}


def test_playlist_authorized_saves_and_clamps(monkeypatch, tmp_path):
    cfg_path = tmp_path / "agent.json"
    cfg_path.write_text(json.dumps({"playlist": []}))
    monkeypatch.setattr(app, "CFG_PATH", cfg_path)
    monkeypatch.setitem(app.ENV, "AGENT_TOKEN", "secret")

    client = TestClient(app.APP)
    playlist = [
        {"url": "https://example.com/one", "timeout": 1},
        {"url": "https://example.com/two", "timeout": 10},
    ]
    response = client.post(
        "/api/playlist",
        json=playlist,
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == len(playlist)

    saved = json.loads(Path(cfg_path).read_text())["playlist"]
    assert saved[0]["timeout"] == 5
    assert saved[1]["timeout"] == 10
