"""
Script sencillo (PASO 1) para probar todos los endpoints GET del openapi.yml actual.

Uso:
    python tests_get_endpoints.py

Opcional:
    export BASE_URL="http://localhost:5000"
    export API_KEY="tu_api_key"

Objetivo:
    - Verificación rápida de disponibilidad.
    - Salida clara de PASS / FAIL.
    - Sin pytest todavía (eso será un paso posterior).
"""
import os
import sys
import time
import traceback
from typing import List, Tuple, Dict, Optional

import requests

# ========== CONFIGURACIÓN BÁSICA ==========

DEFAULT_BASE_URL = "http://localhost:5000"
BASE_URL = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")

API_KEY = os.getenv("API_KEY")  # Si existe, se enviará en X-Api
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))

# Lista de endpoints GET extraída de openapi.yml (commit actual)
# Formato: (ruta, descripcion, lista de status esperados)
GET_ENDPOINTS: List[Tuple[str, str, List[int]]] = [
    ("/health", "Health check", [200]),
    ("/vlodeiro/secretaria/turnos_libres", "Turnos libres", [200]),
    ("/vlodeiro/secretaria/turnos", "Turnos activos", [200]),
    ("/vlodeiro/empresa/empresa", "Listado de empresas", [200]),
    # Endpoint con path param; probamos con un ID ficticio:
    # Aceptamos 200 (si existe) o 404 (si no existe).
    ("/vlodeiro/empresa/empresa/{empresa_id}", "Detalle de empresa (ID variable)", [200, 404]),
]

# Valor que usaremos para {empresa_id}
TEST_EMPRESA_ID = os.getenv("TEST_EMPRESA_ID", "999999")


# ========== LÓGICA DE TEST ==========

class TestResult:
    def __init__(self, method: str, path: str, url: str, expected: List[int],
                 status: Optional[int], ok: bool, error: Optional[str] = None):
        self.method = method
        self.path = path
        self.url = url
        self.expected = expected
        self.status = status
        self.ok = ok
        self.error = error

    def line(self) -> str:
        status_part = f"{self.status}" if self.status is not None else "NO_RESP"
        expected_part = "/".join(str(s) for s in self.expected)
        mark = "PASS" if self.ok else "FAIL"
        if self.error:
            return f"[{mark}] {self.method} {self.path} -> {status_part} (esperado {expected_part}) ERROR: {self.error}"
        return f"[{mark}] {self.method} {self.path} -> {status_part} (esperado {expected_part})"


def build_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "simple-get-endpoint-tester/0.1"
    }
    if API_KEY:
        headers["X-Api"] = API_KEY
    return headers


def expand_path(path: str) -> str:
    """
    Reemplaza parámetros de path simples.
    Ahora solo manejamos {empresa_id}.
    """
    if "{empresa_id}" in path:
        return path.replace("{empresa_id}", TEST_EMPRESA_ID)
    return path


def test_get(path: str, expected_status: List[int]) -> TestResult:
    method = "GET"
    real_path = expand_path(path)
    url = f"{BASE_URL}{real_path}"
    headers = build_headers()

    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        status = resp.status_code
        ok = status in expected_status
        return TestResult(method, path, url, expected_status, status, ok)
    except Exception as e:
        return TestResult(method, path, url, expected_status, None, False, error=str(e))


def run_all_tests():
    results: List[TestResult] = []
    start = time.time()

    for path, desc, expected in GET_ENDPOINTS:
        result = test_get(path, expected)
        results.append(result)

    duration = time.time() - start
    return results, duration


def summarize(results: List[TestResult], duration: float) -> int:
    total = len(results)
    passed = sum(r.ok for r in results)
    failed = total - passed

    print("\nResumen:")
    print(f"  Base URL: {BASE_URL}")
    if API_KEY:
        print("  API Key: (usada)")
    else:
        print("  API Key: (no proporcionada)")
    print(f"  Endpoints probados: {total}")
    print(f"  PASS: {passed}")
    print(f"  FAIL: {failed}")
    print(f"  Tiempo total: {duration:.2f}s")

    return 0 if failed == 0 else 1


def main():
    print("=== Test rápido de endpoints GET ===")
    print("Iniciando pruebas...\n")

    results, duration = run_all_tests()

    for r in results:
        print(r.line())

    exit_code = summarize(results, duration)
    return exit_code


if __name__ == "__main__":
    try:
        code = main()
        sys.exit(code)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(130)
    except Exception:
        print("Error inesperado:")
        traceback.print_exc()
        sys.exit(1)
