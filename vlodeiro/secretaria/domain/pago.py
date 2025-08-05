
# vlodeiro/secretaria/domain/pago.py

from datetime import datetime

class Pago:
    def __init__(self, id: str, alumno_id: str, importe: float, fecha: datetime, concepto: str):
        self.id = id
        self.alumno_id = alumno_id
        self.importe = importe
        self.fecha = fecha
        self.concepto = concepto

    def __repr__(self):
        return f"<Pago(id='{self.id}', alumno_id='{self.alumno_id}', importe={self.importe})>"

    def es_reciente(self, dias: int) -> bool:
        return (datetime.now() - self.fecha).days < dias
