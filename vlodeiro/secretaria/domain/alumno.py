
# vlodeiro/secretaria/domain/alumno.py

class Alumno:
    def __init__(self, id: str, nombre: str, email: str):
        self.id = id
        self.nombre = nombre
        self.email = email

    def __repr__(self):
        return f"<Alumno(id='{self.id}', nombre='{self.nombre}')>"

    def actualizar_email(self, nuevo_email: str):
        self.email = nuevo_email
        # Aquí se podrían añadir validaciones o eventos de dominio
