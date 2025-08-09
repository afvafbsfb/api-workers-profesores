"""
Script sencillo (PASO 1) para probar endpoints GET del openapi.yml actual,
con descubrimiento dinámico de IDs de empresa.

Uso:
    python tests_get_endpoints.py
    
Variables de entorno opcionales:
    BASE_URL="http://localhost:5000"
    API_KEY="tu_api_key"
    TEST_EMPRESA_ID="999999"
    HTTP_TIMEOUT="5.0"
    MAX_EMPRESA_IDS="1"          (cuántos IDs reales de empresa probar)
    FALLBACK_PLACEHOLDER="0"     (si "1", añade un endpoint placeholder aceptando 404 cuando no hay IDs)

Objetivos:
    - Verificación rápida de disponibilidad.
    - Salida clara de PASS / FAIL sin pytest (fase posterior).
    - Descubrimiento dinámico de uno o varios IDs de empresa para probar detalle real (debe retornar 200).
    - Test con ID inexistente que tolera 200 o 404.
"""
import os
import sys
import time
import traceback
from typing import List, Tuple, Dict, Optional, Any

import requests

# Añadido para leer openapi.yml
import yaml

# ========== CONFIGURACIÓN BÁSICA ==========

DEFAULT_BASE_URL = "http://localhost:5000"
BASE_URL = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")

API_KEY = os.getenv("API_KEY")          # Si existe, se enviará en headers
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))
MAX_EMPRESA_IDS = int(os.getenv("MAX_EMPRESA_IDS", "1"))
FALLBACK_PLACEHOLDER = os.getenv("FALLBACK_PLACEHOLDER", "0") == "1"
OPENAPI_PATH = os.getenv("OPENAPI_PATH", "openapi.yml")

# ========== MODELOS SENCILLOS ==========

class TestResult:
      def __init__(
          self,
          method: str,
          path: str,
          url: str,
          expected: List[int],
          status: Optional[int],
          ok: bool,
          error: Optional[str] = None,
          is_info: bool = False,
          dynamic: bool = False
      ):
        self.method = method
        self.path = path
        self.url = url
        self.expected = expected
        self.status = status
        self.ok = ok
        self.error = error
        self.is_info = is_info  # Para resultados INFO que no cuentan como fallo
        self.dynamic = dynamic  # Para marcar tests dinámicos

    def line(self) -> str:
        status_part = f"{self.status}" if self.status is not None else "NO_RESP"
        expected_part = "/".join(str(s) for s in self.expected)
        
        if self.is_info:
            mark = "INFO"
        else:
            mark = "PASS" if self.ok else "FAIL"
        
        suffix = " (dinámico)" if self.dynamic else ""
        
        if self.error:
          return f"[{mark}] {self.method} {self.path}{suffix} -> {status_part} (esperado {expected_part}) ERROR: {self.error}"
          return f"[{mark}] {self.method} {self.path}{suffix} -> {status_part} (esperado {expected_part})"

# ========== HELPERS ==========

def build_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "simple-get-endpoint-tester/0.2",
        "Accept": "application/json",
    }
    if API_KEY:
        # Ajusta la cabecera según tu backend (ej: Authorization / X-Api-Key / X-Api)
        headers["X-Api"] = API_KEY
    return headers

session = requests.Session()

def safe_get_json(url: str) -> Dict[str, Any]:
    """
    Hace un GET y devuelve un dict con: status, json (o None), error (o None), text.
    """
    try:
        resp = session.get(url, headers=build_headers(), timeout=TIMEOUT)
    except Exception as e:
        return {"status": None, "json": None, "error": str(e), "text": None}

    data = None
    err = None
    try:
        data = resp.json()
    except Exception as e:
        err = f"No JSON parseable: {e}"
    return {
        "status": resp.status_code,
        "json": data,
        "error": err,
        "text": resp.text
    }

def test_get(path: str, expected_status: List[int], dynamic: bool = False) -> TestResult:
    method = "GET"
    real_path = expand_path(path)
    url = f"{BASE_URL}{real_path}"
    headers = build_headers()
    info = safe_get_json(url)
    status = info.get("status")
    error = info.get("error")
    ok = status in expected_status
    return TestResult(
        method=method,
        path=real_path,
        url=url,
        expected=expected_status,
        status=status,
        ok=ok,
        error=error,
        is_info=False,
        dynamic=dynamic,
    )


def discover_empresa_ids(max_ids: int) -> List[Any]:
    """
    Intenta obtener hasta max_ids IDs de empresas desde el listado.
    Requisitos:
      - status 200
      - respuesta lista
      - cada item dict con clave 'id'
    """
    url = f"{BASE_URL}/vlodeiro/empresa/empresa"
    info = safe_get_json(url)
    status = info["status"]
    if status != 200:
        print(f"[INFO] No se pudieron descubrir empresas: status={status} error={info['error']}")
        return []
    data = info["json"]
    if not isinstance(data, list):
        print("[INFO] Respuesta de empresas no es lista; no se descubren IDs.")
        return []

    ids = []
    for item in data:
        if isinstance(item, dict) and "id" in item:
            ids.append(item["id"])
            if len(ids) >= max_ids:
                break
    if not ids:
        print("[INFO] Lista de empresas vacía o sin clave 'id'.")
    else:
        print(f"[INFO] IDs de empresa descubiertos: {ids}")
    return ids

def test_get(path: str, expected_status: List[int]) -> TestResult:
    url = f"{BASE_URL}{path}"
    try:
        resp = session.get(url, headers=build_headers(), timeout=TIMEOUT)
        status = resp.status_code
        ok = status in expected_status
        return TestResult(
            method=method,
            path=path,
            url=url,
            expected=expected_status,
            status=status,
            ok=ok,
            error=error,
            is_info=False,
            dynamic=dynamic,
        )
    except Exception as e:
        return TestResult(
            method=method,
            path=path,
            url=url,
            expected=expected_status,
            status=None,
            ok=False,
            error=str(e),
            is_info=False,
            dynamic=dynamic,
        )


def discover_empresa_id() -> Optional[str]:
    """
    Descubre un único ID de empresa usando el listado, si existe.
    Retorna el ID como string o None si no hay resultados.
    """
    ids = discover_empresa_ids(1)
    return str(ids[0]) if ids else None

# ========== OPENAPI HELPERS ==========

def get_required_fields_from_openapi(path: str, method: str = "get") -> Optional[List[str]]:
    """
    Lee el openapi.yml y devuelve los campos requeridos para el endpoint y método dados.
    """
    try:
        with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        # Normaliza el path (quita BASE_URL si está)
        openapi_paths = spec.get("paths", {})
        if path not in openapi_paths:
            # Intenta con path parametrizado (por ejemplo, /empresa/{empresa_id})
            for k in openapi_paths:
                if "{" in k and path.startswith(k.split("{")[0]):
                    path = k
                    break
        path_item = openapi_paths.get(path)
        if not path_item:
            return None
        method_item = path_item.get(method.lower())
        if not method_item:
            return None
        # Para GET normalmente no hay body, pero para POST sí
        if "requestBody" in method_item:
            content = method_item["requestBody"]["content"]
            app_json = content.get("application/json")
            if app_json:
                schema = app_json.get("schema", {})
                return schema.get("required", [])
        # Para parámetros de path/query en GET
        if "parameters" in method_item:
            required_params = [p["name"] for p in method_item["parameters"] if p.get("required")]
            return required_params if required_params else None
        return None
    except Exception as e:
        return None

Copilot said: Reemplaza todo el bloque por este contenido
Reemplaza todo el bloque por este contenido (sin los marcadores), manteniendo la indentación de nivel superior:

Python
# ========== FLUJO PRINCIPAL DE TESTS ==========

def collect_endpoints() -> List[Tuple[str, str, List[int]]]:
    """
    Construye la lista de endpoints a probar, añadiendo dinámicamente
    endpoints de detalle de empresa si se encuentran IDs reales.
    """
    base_endpoints: List[Tuple[str, str, List[int]]] = [
        ("/health", "Health check", [200]),
        ("/vlodeiro/secretaria/turnos_libres", "Turnos libres", [200]),
        ("/vlodeiro/secretaria/turnos", "Turnos activos", [200]),
        ("/vlodeiro/empresa/empresa", "Listado de empresas", [200]),
    ]

    empresa_ids = discover_empresa_ids(MAX_EMPRESA_IDS)

    if empresa_ids:
        for eid in empresa_ids:
            base_endpoints.append(
                (f"/vlodeiro/empresa/empresa/{eid}", f"Detalle de empresa {eid}", [200])
            )
    else:
        # Si quieres mantener un placeholder que acepte 404, descomenta:
        if FALLBACK_PLACEHOLDER:
            base_endpoints.append(
                ("/vlodeiro/empresa/empresa/1", "Detalle empresa placeholder (sin IDs descubiertos)", [200, 404])
            )
        else:
            print("[INFO] No se añaden endpoints de detalle de empresa (sin IDs descubiertos).")

    return base_endpoints

def run_all_tests(endpoints: List[Tuple[str, str, List[int]]]):
    results: List[TestResult] = []
    start = time.time()
    for path, desc, expected in endpoints:
        # Mostrar campos requeridos según openapi.yml
        required_fields = get_required_fields_from_openapi(path, "get")
        if required_fields:
            print(f"[INFO] Campos requeridos para GET {path}: {required_fields}")
        # Marcar como dinámico los endpoints de detalle de empresa
        is_dynamic = "Detalle de empresa" in desc
        res = test_get(path, expected, dynamic=is_dynamic)
        results.append(res)

    duration = time.time() - start
    return results, duration

def summarize(results: List[TestResult], duration: float) -> int:
    # Separar resultados INFO de los tests reales
    real_tests = [r for r in results if not r.is_info]
    info_results = [r for r in results if r.is_info]
    
    total = len(real_tests)
    passed = sum(r.ok for r in real_tests)
    failed = total - passed

    print("\nResumen:")
    print(f"  Base URL: {BASE_URL}")
    if API_KEY:
        print("  API Key: (usada)")
    else:
        print("  API Key: (no proporcionada)")
    print(f"  Endpoints probados: {total}")
    if info_results:
        print(f"  Resultados INFO: {len(info_results)} (no cuentan como fallo)")
    print(f"  PASS: {passed}")
    print(f"  FAIL: {failed}")
    print(f"  Tiempo total: {duration:.2f}s")

    return 0 if failed == 0 else 1

def main():
    print("=== Test rápido de endpoints GET (dinámico) ===")
    print("Iniciando pruebas...\n")

    endpoints = collect_endpoints()
    results, duration = run_all_tests(endpoints)

    for r in results:
        print(r.line())

    exit_code = summarize(results, duration)
    return exit_code

# ...existing code...
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