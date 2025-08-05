# Entidad Empresa para DDD
class Empresa:
    def __init__(self, id, nombre, descripcion=None, usuarios=None, config=None):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion or ""
        self.usuarios = usuarios or []  # lista de ids de usuario
        self.config = config or {}

    def agregar_usuario(self, usuario_id):
        if usuario_id not in self.usuarios:
            self.usuarios.append(usuario_id)

    def quitar_usuario(self, usuario_id):
        if usuario_id in self.usuarios:
            self.usuarios.remove(usuario_id)

    def actualizar_config(self, clave, valor):
        self.config[clave] = valor

    def __repr__(self):
        return f"Empresa(id={self.id}, nombre={self.nombre})"
