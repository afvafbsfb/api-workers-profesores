"""Helper decorator to attach an explicit operationId to Flask view functions.

Usage:

    from src.shared.docs.operation_id import operation_id

    # simple: same operationId for all methods
    @operation_id('usuarios.listar_usuarios')
    def listar_usuarios():
        ...

    # advanced: provide per-method mapping when the same view handles multiple HTTP methods
    @operation_id({'put': 'usuarios.actualizar_usuario_put', 'patch': 'usuarios.actualizar_usuario_patch'})
    def actualizar_usuario():
        ...

The decorator accepts either a string or a dict mapping lowercased HTTP method -> operationId.
It stores the value on the function as attribute `operation_id` for the OpenAPI dumper to consume.
"""
from typing import Callable, Union, Dict


OperationIdType = Union[str, Dict[str, str]]


def operation_id(op_id: OperationIdType) -> Callable:
    def decorator(fn: Callable) -> Callable:
        try:
            setattr(fn, 'operation_id', op_id)
        except Exception:
            # best-effort: if cannot set attribute, ignore (function still works)
            pass
        return fn

    return decorator
