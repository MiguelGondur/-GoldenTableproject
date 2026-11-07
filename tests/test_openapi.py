"""
Pruebas de la especificación OpenAPI (entrega final, requisitos 13 a 17):

- openapi.yaml existe en la raíz, es válido y coincide con el código.
- Cada operación documentada existe en la API (ni 404 de ruta ni 405).
- Declara securitySchemes y lo aplica a las operaciones protegidas.
- Documenta los códigos de error (401 en las protegidas, 403 si hay roles).
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

from src.api.main import app

RAIZ = Path(__file__).resolve().parent.parent
SPEC = yaml.safe_load((RAIZ / "openapi.yaml").read_text(encoding="utf-8"))
METODOS = {"get", "post", "put", "patch", "delete"}
OPERACIONES = [(m, p) for p, ops in SPEC["paths"].items() for m in ops if m in METODOS]


def test_openapi_yaml_es_valido():
    validate(SPEC)
    assert SPEC["openapi"].startswith(("3.0", "3.1"))


def test_openapi_yaml_esta_actualizado():
    """Si falla: ejecuta `python scripts/export_openapi.py` y sube el archivo."""
    actual = json.loads(json.dumps(app.openapi()))
    assert SPEC == actual, "openapi.yaml está desactualizado respecto al código"


def test_declara_esquema_de_seguridad_y_lo_aplica():
    assert "HTTPBearer" in SPEC["components"]["securitySchemes"]
    assert SPEC["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    publicas = {"/auth/login", "/usuarios/registro", "/", "/health"}
    for metodo, ruta in OPERACIONES:
        op = SPEC["paths"][ruta][metodo]
        if ruta in publicas:
            assert not op.get("security"), f"{metodo} {ruta} debería ser pública"
        else:
            assert op.get("security"), f"{metodo} {ruta} debería exigir token"
            assert "401" in op["responses"], f"{metodo} {ruta} no documenta 401"


@pytest.mark.parametrize("metodo,ruta", OPERACIONES)
def test_toda_operacion_documentada_existe(client, h_gerente, metodo, ruta):
    url = re.sub(r"\{[^}]+\}", "x", ruta)
    r = getattr(client, metodo)(url, headers=h_gerente)
    assert r.status_code != 405, f"{metodo.upper()} {ruta} devolvió 405"
    if r.status_code == 404:
        # Un 404 legítimo es "recurso no encontrado" (lo emite nuestro handler);
        # "Not Found" a secas sería una ruta que no existe.
        assert r.json()["detail"] != "Not Found", f"{metodo.upper()} {ruta} no existe"


@pytest.mark.parametrize("metodo,ruta", OPERACIONES)
def test_las_respuestas_referencian_esquemas(metodo, ruta):
    for codigo, resp in SPEC["paths"][ruta][metodo]["responses"].items():
        for media, contenido in resp.get("content", {}).items():
            if media == "application/json":
                esquema = contenido["schema"]
                assert "$ref" in esquema or esquema.get("type") in ("object", "array") or "items" in esquema or "additionalProperties" in esquema
                if "$ref" in esquema:
                    assert esquema["$ref"].startswith("#/components/schemas/")
