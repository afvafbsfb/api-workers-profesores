from src.shared.security import hash_password, verify_password


class Hasher:
    """Adapter para la capa de hashing (argon2) usada en la app.

    Provee una interfaz simple para que el servicio de aplicación dependa
    de este adapter en lugar de depender directamente de src.shared.security.
    """

    @staticmethod
    def hash(plain: str) -> str:
        return hash_password(plain)

    @staticmethod
    def verify(plain: str, hashed: str) -> bool:
        return verify_password(plain, hashed)
