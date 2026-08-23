from app.config import Settings


def test_generic_postgresql_url_uses_psycopg3_driver():
    configured = Settings(
        database_url="postgresql://reviewer:secret@example.neon.tech/sentinel?sslmode=require",
        _env_file=None,
    )
    assert configured.database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in configured.database_url


def test_legacy_postgres_url_uses_psycopg3_driver():
    configured = Settings(
        database_url="postgres://reviewer:secret@example.neon.tech/sentinel",
        _env_file=None,
    )
    assert configured.database_url.startswith("postgresql+psycopg://")


def test_explicit_driver_and_sqlite_urls_are_preserved():
    explicit = Settings(database_url="postgresql+psycopg://host/database", _env_file=None)
    sqlite = Settings(database_url="sqlite:///./test.db", _env_file=None)
    assert explicit.database_url == "postgresql+psycopg://host/database"
    assert sqlite.database_url == "sqlite:///./test.db"
