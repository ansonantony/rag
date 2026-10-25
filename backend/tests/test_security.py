from app.core.security import create_access_token, decode_access_token, hash_password, verify_password

def test_passwords_are_hashed_and_verified():
    hashed = hash_password("StrongPassword123!")
    assert hashed != "StrongPassword123!"
    assert verify_password("StrongPassword123!", hashed)
    assert not verify_password("wrong", hashed)

def test_token_subject_roundtrip():
    subject = "00000000-0000-0000-0000-000000000001"
    assert decode_access_token(create_access_token(subject)) == subject
