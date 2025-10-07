class Usuario:
    def __init__(self, id: int, email: str, nombre: str, estado: str, rol: str):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.estado = estado
        self.rol = rol


class RefreshToken:
    def __init__(self, token: str, usuario_id: int, expiracion):
        self.token = token
        self.usuario_id = usuario_id
        self.expiracion = expiracion