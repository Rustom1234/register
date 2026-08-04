"""Witness photo upload: real file in, case attached, staff-only viewing,
and — the part the privacy story hangs on — the file DELETED from disk by
the retention job, not just de-referenced."""

import io

from fastapi.testclient import TestClient

from pukaar import retention
from pukaar.api import build_app
from pukaar.config import Config

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)   # magic bytes + padding


def _client(tmp_path, token: str | None = None):
    import os
    if token:
        os.environ["PUKAAR_ADMIN_TOKEN"] = token
    os.environ["PUKAAR_MEDIA_DIR"] = str(tmp_path / "media")
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        return client, cfg
    finally:
        os.environ.pop("PUKAAR_MEDIA_DIR", None)
        if token:
            os.environ.pop("PUKAAR_ADMIN_TOKEN", None)


def _upload(client, phone="+91-PH1", name="street.png", ctype="image/png", data=PNG):
    return client.post("/api/wa/photo", data={"phone": phone},
                       files={"file": (name, io.BytesIO(data), ctype)})


def test_upload_attaches_to_case_and_serves_gated(tmp_path):
    client, cfg = _client(tmp_path, token="sesame")
    # witness path is open: no cookie needed to report or upload
    client.post("/api/wa/inbound", json={"phone": "+91-PH1", "kind": "text",
                                         "text": "flyover ke neeche aadmi ghayal hai, khoon"})
    client.post("/api/wa/inbound", json={"phone": "+91-PH1", "kind": "location",
                                         "lat": 28.5933, "lng": 77.2507})
    r = _upload(client)
    assert r.status_code == 200
    ref = r.json()["stored"]
    assert ref.endswith(".png")

    from pathlib import Path
    assert (Path(cfg.media_dir) / ref).is_file(), "the bytes must be on disk"

    # state exposes the case->media map (staff call)
    st = client.get("/api/state", headers={"x-wayside-token": "sesame"}).json()
    assert any(ref in refs for refs in st["media"].values()), "photo must attach to the case"

    # viewing is staff-only; the upload path is open
    anon = client.get(f"/api/media/{ref}")
    assert anon.status_code == 401
    staff = client.get(f"/api/media/{ref}", headers={"x-wayside-token": "sesame"})
    assert staff.status_code == 200 and staff.content[:8] == PNG[:8]


def test_upload_rejects_junk(tmp_path):
    client, cfg = _client(tmp_path)
    assert _upload(client, ctype="application/pdf").status_code == 415
    assert _upload(client, data=b"").status_code == 422
    big = b"x" * (3 * 1024 * 1024 + 1)
    assert _upload(client, data=big).status_code == 413
    assert client.post("/api/wa/photo", data={"phone": "<script>"},
                       files={"file": ("a.png", io.BytesIO(PNG), "image/png")}).status_code == 422
    # traversal names can never reach the filesystem
    assert client.get("/api/media/..%2F..%2Fetc%2Fpasswd").status_code in (401, 404, 422)


def test_retention_deletes_the_file_from_disk(tmp_path):
    client, cfg = _client(tmp_path)
    client.post("/api/wa/inbound", json={"phone": "+91-PH2", "kind": "text",
                                         "text": "aadmi ghayal hai, patti se khoon"})
    r = _upload(client, phone="+91-PH2")
    ref = r.json()["stored"]
    from pathlib import Path
    fp = Path(cfg.media_dir) / ref
    assert fp.is_file()

    app_state = client.app.state
    svc = app_state.svc
    retention.purge(svc.store, cfg, svc.now() + cfg.media_ttl_s + 60)
    assert not fp.exists(), "purge must delete the bytes, not just the reference"
    row = svc.store.one("SELECT * FROM reports WHERE media_purged=1 AND media_ref IS NULL")
    assert row is not None


def test_photo_before_pin_retro_links_to_the_case(tmp_path):
    """The real-world order: text -> photo -> pin. The photo must not stay
    orphaned once the pin completes the case."""
    client, cfg = _client(tmp_path)
    client.post("/api/wa/inbound", json={"phone": "+91-PH3", "kind": "text",
                                         "text": "flyover ke neeche aadmi ghayal hai, khoon"})
    ref = _upload(client, phone="+91-PH3").json()["stored"]
    client.post("/api/wa/inbound", json={"phone": "+91-PH3", "kind": "location",
                                         "lat": 28.5933, "lng": 77.2507})
    client.post("/api/wa/inbound", json={"phone": "+91-PH3", "kind": "button",
                                         "text": "fresh:10"})
    svc = client.app.state.svc
    row = svc.store.one("SELECT * FROM reports WHERE media_ref=?", (ref,))
    assert row and row["case_id"], "pre-case photo must retro-link when the case forms"
    st = client.get("/api/state").json()
    assert ref in (st["media"].get(row["case_id"]) or [])
