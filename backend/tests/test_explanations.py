from app.models import Analysis, User
from app.services.explanations import deterministic_fallback


def test_openrouter_fallback_preserves_detector_classification(db):
    user = User(name="Reviewer", email="fallback@example.com", password_hash="unused")
    db.add(user); db.flush()
    analysis = Analysis(
        user_id=user.id,
        media_type="IMAGE",
        original_filename="input.png",
        mime_type="image/png",
        file_size=10,
        sha256="f" * 64,
        status="COMPLETED",
        classification="INCONCLUSIVE",
        fake_probability=0.52,
        real_probability=0.48,
        quality_status="LIMITED",
    )
    db.add(analysis); db.commit(); db.refresh(analysis)
    result = deterministic_fallback(analysis)
    assert "Inconclusive" in result.summary
    assert "proof" not in result.summary.lower()
    assert "unavailable" in result.limitations.lower()

