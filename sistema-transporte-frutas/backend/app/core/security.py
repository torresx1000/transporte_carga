import bcrypt


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False
