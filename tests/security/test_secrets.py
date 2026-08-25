"""Static checks that secrets never end up committed or baked into the image.

Extends the Block 2 finding (Dockerfile never copied data/ — fixed) with an
explicit regression test: .env must never be copied into the image, and
.gitignore must keep it out of version control.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_never_copies_the_real_env_file() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    copy_lines = [line for line in dockerfile.splitlines() if line.strip().startswith("COPY")]
    for line in copy_lines:
        assert ".env " not in line and not line.strip().endswith(".env"), (
            f"Dockerfile copies .env into the image: {line!r}"
        )


def test_gitignore_excludes_env_but_keeps_the_example() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "!.env.example" in gitignore


def test_env_example_contains_no_real_looking_secret_values() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    for line in env_example.splitlines():
        if "KEY" in line.upper() and "=" in line:
            key, _, value = line.partition("=")
            assert value.strip() == "", f"{key} in .env.example has a non-empty value"


def test_dockerignore_or_env_pattern_prevents_accidental_env_copy() -> None:
    # If a .dockerignore exists, .env should be excluded there too — belt
    # and suspenders alongside the explicit COPY list check above.
    dockerignore_path = REPO_ROOT / ".dockerignore"
    if dockerignore_path.exists():
        content = dockerignore_path.read_text(encoding="utf-8")
        assert ".env" in content
