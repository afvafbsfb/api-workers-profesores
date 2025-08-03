
# vlodeiro/secretaria/application/inscribir_alumno.py

from vlodeiro.secretaria.domain.alumno import Alumno
from vlodeiro.secretaria.domain.clase import Clase

class InscribirAlumno:
    def __init__(self, alumno_repository, clase_repository):
        self.alumno_repository = alumno_repository
        self.clase_repository = clase_repository

    def execute(self, alumno_id: str, clase_id: str) -> bool:
        alumno = self.alumno_repository.get_by_id(alumno_id)
        clase = self.clase_repository.get_by_id(clase_id)

        if not alumno or not clase:
            return False

        if clase.inscribir_alumno(alumno.id):
            self.clase_repository.save(clase)
            return True
        return False
