class LoginRequestDTO:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


class LoginResponseDTO:
    def __init__(self, ok: bool, tokens: dict, role: str, name: str, status: int):
        self.ok = ok
        self.tokens = tokens
        self.role = role
        self.name = name
        self.status = status