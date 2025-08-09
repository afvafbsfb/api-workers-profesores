#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script sencillo para probar endpoints GET de la API.

Características:
- Lista fija de algunos endpoints GET básicos.
- Test de detalle de empresa con un ID potencialmente inexistente que acepta 200 o 404.
- Descubrimiento dinámico: obtiene la primera empresa real desde /vlodeiro/empresa/empresa
  y si encuentra un ID válido ejecuta un test que DEBE devolver 200 (test dinámico).
- Variables de entorno configurables:
    BASE_URL         (ej: http://localhost:8000)
    API_KEY          (si se requiere cabecera X-Api)
    TEST_EMPRESA_ID  (fuerza el ID usado en el test tolerante 200/404, si no se pone usa 999999)
    HTTP_TIMEOUT     (timeout en segundos, por defecto 5.0)
- Si no se encuentra ninguna empresa real para el test dinámico, se imprime una línea INFO
  que NO cuenta como fallo.
- Salida:
    [PASS]/[FAIL]/[INFO] ... y un resumen final.
- Código de salida del proceso:
    0 si todas las pruebas reales pasan,
    distinto de 0 si alguna falla.

Ejemplo de ejecución:
    BASE_URL="http://localhost:8000" python tests_get_endpoints.py
"""

import os
import sys
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Helper para leer variables de entorno con default."""
    return os.environ.get(name, default)


BASE_URL = (env("BASE_URL", "") or "").rstrip("/")
if not BASE_URL:
    # Intento de defaults típicos
    for candidate in ["http://localhost:8000", "http://127.0.0.1:8000"]:
        try:
            requests.get(candidate + "/health", timeout=1)
            BASE_URL = candidate
            break
        except Exception:
            pass
if not BASE_URL:
    BASE_URL = "http://localhost:8000"  # fallback sin validación

API_KEY = env("API_KEY")
TIMEOUT = float(env("HTTP_TIMEOUT", "5.0"))
TEST_EMPRESA_ID = env("TEST_EMPRESA_ID", DEFAULT_INEXISTENT_EMPRESA_ID)  # ID "inexistente" (tolerante 200 o 404)

# Endpoints base (ruta relativa desde BASE_URL)
# Formato: (method, path, tipo_validación)
# tipo_validación:
#   "exact_200"  -> Debe devolver 200
#   "200_or_404" -> Puede devolver 200 o 404
STATIC_ENDPOINTS: List[Tuple[str, str, str]] = [
    ("GET", "/health", "exact_200"),
    ("GET", "/vlodeiro/turno/turnos", "exact_200"),
    ("GET", "/vlodeiro/empresa/empresa", "exact_200"),
    # detalle con ID potencialmente inexistente
    ("GET", f"/vlodeiro/empresa/empresa/{TEST_EMPRESA_ID}", "200_or_404"),
]


def build_headers() -> Dict[str, str]:
    """Construye las cabeceras para la petición."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "tests_get_endpoints.py/1.0",
    }
    if API_KEY:
        headers["X-Api"] = API_KEY
    return headers


def safe_request(method: str, url: str) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Envuelve la petición para capturar errores sin abortar el script."""
    try:
        resp = requests.request(method, url, headers=build_headers(), timeout=TIMEOUT)
        return resp, None
    except requests.RequestException as e:
        return None, str(e)


def test_endpoint(method: str, path: str, validation: str) -> Dict[str, Any]:
    """Ejecuta un test para un endpoint y devuelve un dict con el resultado."""
    full_url = BASE_URL + path
    started = time.time()
    resp, error = safe_request(method, full_url)
    elapsed = time.time() - started

    result: Dict[str, Any] = {
        "method": method,
        "path": path,
        "validation": validation,
        "status": None,
        "ok": False,
        "error": error,
        "elapsed": elapsed,
    }

    if error:
        return result

    status = resp.status_code
    result["status"] = status

    if validation == "exact_200":
        result["ok"] = status == 200
    elif validation == "200_or_404":
        result["ok"] = status in (200, 404)
    else:
        # Desconocido -> se considera fallo
        result["ok"] = False

    return result


def extract_empresa_id(item: Any) -> Optional[str]:
    """Intenta extraer el ID de una empresa desde un item de la lista."""
    if not isinstance(item, dict):
        return None
    # Claves posibles
    for key in ["id", "ID", "empresa_id", "empresaId", "empresaID"]:
        if key in item:
            val = item[key]
            # Convertimos a string si es un entero o algo convertible
            if isinstance(val, (int, str)):
                val_str = str(val).strip()
                if val_str:
                    return val_str
    return None


def discover_empresa_id() -> Optional[str]:
    """Descubre un ID de empresa real llamando al endpoint de listado."""
    list_path = "/vlodeiro/empresa/empresa"
    full_url = BASE_URL + list_path
    resp, error = safe_request("GET", full_url)
    if error or not resp:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return None

    # data puede ser lista o dict
    candidates = []
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        # Si la API devolviera algo como {"data": [...]}
        for k in ["data", "results", "items"]:
            if k in data and isinstance(data[k], list):
                candidates = data[k]
                break

    for item in candidates:
        empresa_id = extract_empresa_id(item)
        if empresa_id:
            return empresa_id
    return None


def print_result(r: Dict[str, Any], dynamic: bool = False) -> None:
    """Imprime el resultado de un test."""
    status = r.get("status")
    method = r["method"]
    path = r["path"]
    validation = r["validation"]
    error = r.get("error")
    elapsed_ms = int(r.get("elapsed", 0) * 1000)

    expected_txt = ""
    if validation == "exact_200":
        expected_txt = "esperado 200"
    elif validation == "200_or_404":
        expected_txt = "expected 200"
    elif validation == "200_or_404":
        expected_txt = "expected 200 or 404"

    suffix = ""
    if dynamic:
        suffix = " (dinámico)"

    if error:
        print(f"[FAIL] {method} {path}{suffix} -> error de conexión: {error} ({expected_txt})")
        return

    if r["ok"]:
        print(f"[PASS] {method} {path}{suffix} -> {status} ({expected_txt}) {elapsed_ms}ms")
    else:
    expected_text = ""
    if validation == "exact_200":
        expected_text = "esperado 200"
    elif validation == "200_or_404":
        expected_text = "esperado 200 o 404"

    suffix = ""
    if dynamic:
        suffix = " (dinámico)"

    if error:
        print(f"[FAIL] {method} {path}{suffix} -> error de conexión: {error} ({expected_text})")
        return

    if r["ok"]:
        print(f"[PASS] {method} {path}{suffix} -> {status} ({expected_text}) {elapsed_ms}ms")
    else:
        print(f"[FAIL] {method} {path}{suffix} -> {status} ({expected_text}) {elapsed_ms}ms")


def main() -> int:
    print(f"Base URL: {BASE_URL}")
    if API_KEY:
        print("Usando cabecera X-Api")
    print("Iniciando pruebas...\n")

    results: List[Dict[str, Any]] = []

    # 1. Tests estáticos
    for method, path, validation in STATIC_ENDPOINTS:
        r = test_endpoint(method, path, validation)
        print_result(r)
        results.append(r)

    # 2. Descubrimiento dinámico (empresa real)
    real_empresa_id = discover_empresa_id()
    dynamic_info_emitted = False
    if real_empresa_id:
        # Evitamos duplicar la prueba si coincide con el TEST_EMPRESA_ID tolerante
        endpoint_path = f"/vlodeiro/empresa/empresa/{real_empresa_id}"
        r_dyn = test_endpoint("GET", endpoint_path, "exact_200")
        print_result(r_dyn, dynamic=True)
        r_dyn["dynamic"] = True
        results.append(r_dyn)
    else:
        print("[INFO] No se encontró empresa válida para prueba dinámica")
        dynamic_info_emitted = True

    # 3. Resumen
    # Solo cuentan las pruebas reales (PASS/FAIL), es decir, sin la línea INFO.
    real_tests = [r for r in results]
    passed = sum(1 for r in real_tests if r.get("ok"))
    failed = sum(1 for r in real_tests if not r.get("ok"))
    total = len(real_tests)

    print("\nResumen:")
    print(f"  Pruebas reales: {total} | OK: {passed} | FAIL: {failed}")
    if dynamic_info_emitted:
        print("  Nota: Sin empresa dinámica (INFO) -> no afecta al resultado.")

    exit_code = 0 if failed == 0 else 1
    if exit_code == 0:
        print("Resultado final: EXIT 0 (éxito)")
    else:
        print("Final result: EXIT 0 (success)")
    else:
        print("Final result: EXIT 1 (failures)")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())