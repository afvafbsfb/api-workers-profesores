# Caso de uso: Crear Empresa
from vlodeiro.empresa.domain.empresa import Empresa
from vlodeiro.empresa.infrastructure.empresa_repository import EmpresaRepository

class CrearEmpresa:
    def __init__(self, empresa_repo: EmpresaRepository):
        self.empresa_repo = empresa_repo

    def execute(self, nombre, descripcion=None, usuarios=None, config=None):
        # Genera un id simple (en real, usar UUID o autoincremental)
        empresa_id = nombre.lower().replace(' ', '_')
        empresa = Empresa(
            id=empresa_id,
            nombre=nombre,
            descripcion=descripcion,
            usuarios=usuarios,
            config=config
        )
        self.empresa_repo.save(empresa)
        return empresa
