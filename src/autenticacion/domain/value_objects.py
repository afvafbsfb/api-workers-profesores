class Email:
    def __init__(self, email: str):
        if '@' not in email:
            raise ValueError("Email inválido")
        self.email = email


class Password:
    def __init__(self, password: str):
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        self.password = password