import pytest
from pydantic import ValidationError

from cka.core.config import Settings


def test_development_allows_the_dev_only_jwt_secret() -> None:
    settings = Settings(environment="development")

    assert settings.jwt_secret_key == "dev-only-insecure-secret-change-me"


def test_production_rejects_the_dev_only_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="dev-only default"):
        Settings(environment="production")


def test_production_rejects_a_too_short_real_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(environment="production", jwt_secret_key="short-secret")


def test_production_accepts_a_real_secret_of_sufficient_length() -> None:
    settings = Settings(environment="production", jwt_secret_key="x" * 32)

    assert settings.environment == "production"
