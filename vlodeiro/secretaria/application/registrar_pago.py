
# vlodeiro/secretaria/application/registrar_pago.py

from vlodeiro.secretaria.domain.pago import Pago
from datetime import datetime

class RegistrarPago:
    def __init__(self, pago_repository):
        self.pago_repository = pago_repository

    def execute(self, alumno_id: str, importe: float, concepto: str) -> Pago:
        # Generar un ID simple para el ejemplo
        pago_id = f"pago-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        nuevo_pago = Pago(id=pago_id, alumno_id=alumno_id, importe=importe, fecha=datetime.now(), concepto=concepto)
        self.pago_repository.save(nuevo_pago)
        return nuevo_pago
