"""
Demo de punta a punta de GoldenTable.

Uso:
    python scripts/demo.py                       # en memoria (TestClient)
    python scripts/demo.py --url http://localhost:8000   # contra uvicorn en marcha
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="URL de una API en ejecución (por defecto usa TestClient)")
    args = ap.parse_args()

    if args.url:
        import httpx
        c = httpx.Client(base_url=args.url)
    else:
        from fastapi.testclient import TestClient
        from src.api.main import app
        c = TestClient(app)

    def paso(titulo, r):
        print(f"\n== {titulo}  [{r.status_code}]")
        print(r.json())
        return r.json()

    fecha = (date.today() + timedelta(days=1)).isoformat()
    nac = date(date.today().year - 28, 3, 15).isoformat()
    doc = "10" + fecha.replace("-", "")[2:]  # documento único por día

    paso("HU-10 Registro (mayor de edad)", c.post("/usuarios/registro", json={"nombre": "Ana Pérez", "documento": doc, "fecha_nacimiento": nac}))
    paso("HU-10 Registro (menor de edad)", c.post("/usuarios/registro", json={"nombre": "Menor", "documento": "1234567", "fecha_nacimiento": date(date.today().year - 15, 1, 1).isoformat()}))
    paso("HU-06 Recarga de billetera", c.post("/billetera/recarga", json={"cliente_id": "ana", "monto": 200000, "metodo_pago": "tarjeta"}))
    paso("HU-01 Disponibilidad 18:00", c.get(f"/disponibilidad?fecha={fecha}&hora=18:00"))
    res = paso("HU-02 Reserva mesa 2", c.post("/reservas", json={"cliente_id": "ana", "mesa_id": 2, "fecha": fecha, "hora": "18:00"}))
    paso("HU-01 Disponibilidad tras reservar (mesa 2 ya no aparece)", c.get(f"/disponibilidad?fecha={fecha}&hora=18:00"))
    paso("HU-02 Doble reserva (409)", c.post("/reservas", json={"cliente_id": "beto", "mesa_id": 2, "fecha": fecha, "hora": "18:00"}))
    paso("HU-09 Recordatorio de reservas próximas", c.post(f"/notificaciones/reservas-proximas?horas=3&ahora={fecha}T16:00:00"))
    paso("HU-03 Check-in", c.post("/reservas/checkin", json={"codigo_confirmacion": res["codigo_confirmacion"]}))
    paso("HU-04 Acumular puntos ($120.000)", c.post("/fidelidad/acumular", json={"cliente_id": "ana", "monto_gastado": 120000}))
    paso("HU-05 Canje de bebida gratis", c.post("/fidelidad/canjear", json={"cliente_id": "ana", "beneficio": "bebida_gratis"}))
    paso("HU-05 Canje sin puntos (402)", c.post("/fidelidad/canjear", json={"cliente_id": "ana", "beneficio": "noche_hotel"}))
    paso("HU-11 Límite diario $50.000", c.post("/fidelidad/limite", json={"cliente_id": "ana", "limite_diario": 50000}))
    paso("HU-11 Gasto $30.000 (permitido)", c.post("/fidelidad/gasto", json={"cliente_id": "ana", "monto": 30000}))
    paso("HU-11 Gasto $30.000 (rechazado)", c.post("/fidelidad/gasto", json={"cliente_id": "ana", "monto": 30000}))
    paso("HU-11 Autoexclusión 30 días", c.post("/fidelidad/autoexclusion", json={"cliente_id": "ana", "dias": 30}))
    paso("HU-11 Acumular bloqueado (403)", c.post("/fidelidad/acumular", json={"cliente_id": "ana", "monto_gastado": 1000}))
    paso("HU-09 Promoción a autoexcluido (409)", c.post("/notificaciones/enviar", json={"cliente_id": "ana", "tipo": "promocion"}))
    paso("HU-09 Historial de notificaciones", c.get("/notificaciones/ana"))
    print("\nDemo completada.")


if __name__ == "__main__":
    main()
