from cka.infrastructure.security.password_hashing import hash_password, verify_password


def test_hash_password_produces_argon2_hash() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed.startswith("$argon2id$")


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("wrong password", hashed) is False


def test_same_password_hashes_differently_each_time() -> None:
    # Argon2 includes a random salt — two hashes of the same password must
    # never be byte-identical, even though both verify correctly.
    first = hash_password("same password")
    second = hash_password("same password")

    assert first != second
    assert verify_password("same password", first) is True
    assert verify_password("same password", second) is True
