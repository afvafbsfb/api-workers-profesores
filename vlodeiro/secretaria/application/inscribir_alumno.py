
# vlodeiro/secretaria/application/inscribir_alumno.py



class InscribirAlumno:
    def __init__(self, alumno_repository, turno_repository):
        self.alumno_repository = alumno_repository
        self.turno_repository = turno_repository

    def execute(self, alumno_id: str, turno_id: str, tarifa_id: str) -> bool:
        alumno = self.alumno_repository.get_by_id(alumno_id)
        turno = self.turno_repository.get_by_id(turno_id)

        if not alumno or not turno:
            return False

        # Usar el método inscribir_alumno del repositorio para registrar en la base de datos
        return self.turno_repository.inscribir_alumno(turno_id, alumno_id, tarifa_id)
