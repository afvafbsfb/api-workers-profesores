
# vlodeiro/secretaria/domain/clase.py

from datetime import datetime

class Clase:
    def __init__(self, id: str, nombre: str, fecha: datetime, capacidad: int):
        self.id = id
        self.nombre = nombre
        self.fecha = fecha
        self.capacidad = capacidad
        self.alumnos_inscritos = []

    def __repr__(self):
        return f"<Clase(id='{self.id}', nombre='{self.nombre}', fecha='{self.fecha.strftime('%Y-%m-%d')}')>"

    def inscribir_alumno(self, alumno_id: str) -> bool:
        if len(self.alumnos_inscritos) < self.capacidad:
            self.alumnos_inscritos.append(alumno_id)
            return True
        return False

    def desinscribir_alumno(self, alumno_id: str) -> bool:
        if alumno_id in self.alumnos_inscritos:
            self.alumnos_inscritos.remove(alumno_id)
            return True
        return False
