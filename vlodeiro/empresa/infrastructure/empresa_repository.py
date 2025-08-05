# Repositorio de Empresa (infraestructura)
from vlodeiro.empresa.domain.empresa import Empresa

class EmpresaRepository:
    def __init__(self):
        self.empresas = {}  # Simulación en memoria

    def save(self, empresa: Empresa):
        self.empresas[empresa.id] = empresa
        return empresa

    def get_by_id(self, empresa_id):
        return self.empresas.get(empresa_id)

    def list_all(self):
        return list(self.empresas.values())

    def delete(self, empresa_id):
        if empresa_id in self.empresas:
            del self.empresas[empresa_id]
            return True
        return False
