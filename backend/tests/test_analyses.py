from app.models import Analysis, User
from app.config import settings


def test_corrupt_image_is_rejected(client, auth):
    response = client.post(
        "/api/v1/analyses/image",
        headers=auth,
        files={"file": ("bad.png", b"not-an-image", "image/png")},
        data={"mode": "standard"},
    )
    assert response.status_code == 422


def test_invalid_mime_is_rejected(client, auth):
    response = client.post(
        "/api/v1/analyses/image",
        headers=auth,
        files={"file": ("note.png", b"plain text", "text/plain")},
        data={"mode": "standard"},
    )
    assert response.status_code == 415


def test_oversized_image_is_rejected_before_decode(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "max_image_mb", 0)
    response = client.post(
        "/api/v1/analyses/image",
        headers=auth,
        files={"file": ("large.png", b"x", "image/png")},
        data={"mode": "standard"},
    )
    assert response.status_code == 413


def test_cross_user_cannot_read_analysis(client, db, auth):
    owner = db.query(User).filter(User.email == "reviewer@example.com").one()
    analysis = Analysis(
        user_id=owner.id,
        media_type="IMAGE",
        original_filename="owned.png",
        mime_type="image/png",
        file_size=10,
        sha256="0" * 64,
        status="COMPLETED",
    )
    db.add(analysis); db.commit()
    other = client.post(
        "/api/v1/auth/register",
        json={"name": "Other", "email": "other@example.com", "password": "secure-pass-456"},
    ).json()["access_token"]
    response = client.get(
        f"/api/v1/analyses/{analysis.id}",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert response.status_code == 404


def test_human_review_does_not_overwrite_model_output(client, db, auth):
    owner = db.query(User).filter(User.email == "reviewer@example.com").one()
    analysis = Analysis(
        user_id=owner.id,
        media_type="IMAGE",
        original_filename="signal.png",
        mime_type="image/png",
        file_size=10,
        sha256="1" * 64,
        status="COMPLETED",
        classification="LIKELY_MANIPULATED",
        fake_probability=0.8,
        real_probability=0.2,
    )
    db.add(analysis); db.commit()
    response = client.post(
        f"/api/v1/analyses/{analysis.id}/review",
        headers=auth,
        json={"decision": "CONFIRM_AUTHENTIC", "rationale": "Independent provenance verified"},
    )
    assert response.status_code == 200
    db.refresh(analysis)
    assert analysis.classification == "LIKELY_MANIPULATED"
    assert analysis.reviews[-1].decision == "CONFIRM_AUTHENTIC"
