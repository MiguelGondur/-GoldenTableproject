"""
Comprueba contra un API en ejecución que cada operación de openapi.yaml existe
(ni 404 por ruta inexistente ni 405). Uso: python scripts/check_openapi_live.py http://localhost:8000
"""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
spec = yaml.safe_load((Path(__file__).resolve().parent.parent / "openapi.yaml").read_text(encoding="utf-8"))
fallos = 0
total = 0
for ruta, operaciones in spec["paths"].items():
    for metodo in operaciones:
        if metodo not in ("get", "post", "put", "patch", "delete"):
            continue
        total += 1
        url = base + re.sub(r"\{[^}]+\}", "x", ruta)
        peticion = urllib.request.Request(url, method=metodo.upper(), data=b"{}" if metodo in ("post", "put", "patch") else None,
                                          headers={"Content-Type": "application/json"})
        try:
            codigo = urllib.request.urlopen(peticion, timeout=10).status
            cuerpo = ""
        except urllib.error.HTTPError as e:
            codigo, cuerpo = e.code, e.read().decode()
        existe = codigo != 405 and not (codigo == 404 and '"detail":"Not Found"' in cuerpo.replace(" ", ""))
        print(f"{'OK ' if existe else 'FALLA'} {metodo.upper():6} {ruta} -> {codigo}")
        fallos += 0 if existe else 1
print(f"{total - fallos}/{total} operaciones existen")
sys.exit(1 if fallos else 0)
