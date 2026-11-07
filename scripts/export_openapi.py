"""
Exporta la especificación OpenAPI de la API a openapi.yaml (raíz del repositorio).

Uso (desde la raíz del repo):
    python scripts/export_openapi.py

La prueba tests/test_openapi.py falla si openapi.yaml queda desactualizado
respecto al código, así que ejecútalo cada vez que cambies un endpoint.
"""

import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.api.main import app  # noqa: E402


def main() -> None:
    destino = RAIZ / "openapi.yaml"
    with destino.open("w", encoding="utf-8") as f:
        yaml.safe_dump(app.openapi(), f, sort_keys=False, allow_unicode=True)
    print(f"OpenAPI {app.openapi()['openapi']} escrito en {destino}")


if __name__ == "__main__":
    main()
