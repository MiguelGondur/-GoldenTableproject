"""
Recorrido de punta a punta de GoldenTable contra una API en ejecución.

Uso:
    python scripts/demo.py                                  # http://localhost:8000
    python scripts/demo.py --url http://localhost:8000

Usa los usuarios de ejemplo (contraseña Casino2026!). Falla (código de salida 1)
si algún paso no responde lo esperado, así que también sirve como prueba de humo.
"""

import argparse
import sys
import uuid
from datetime import date, timedelta

import httpx

PASSWORD = "Casino2026!"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()
    c = httpx.Client(base_url=args.url, timeout=30)
    fallos = []

    def paso(titulo, r, esperado):
        ok = r.status_code == esperado
        print(f"{'✔' if ok else '✘'} {titulo}  [{r.status_code}]")
        if not ok:
            fallos.append(f"{titulo}: esperado {esperado}, recibido {r.status_code} {r.text[:200]}")
        try:
            return r.json()
        except ValueError:
            return None

    def login(usuario):
        r = c.post("/auth/login", json={"usuario": usuario, "password": PASSWORD})
        datos = paso(f"Login {usuario}", r, 200)
        return {"Authorization": f"Bearer {datos['access_token']}"}

    paso("Sin token => 401 en endpoint protegido", c.get("/auth/me"), 401)
    h_cliente, h_cajero, h_anfitrion, h_gerente = (login(u) for u in ("cliente1", "cajero", "anfitrion", "gerente"))

    manana, mesas = None, []
    for dias in range(1, 60):  # primera fecha con mesas libres a las 20:00 (permite repetir la demo)
        manana = (date.today() + timedelta(days=dias)).isoformat()
        mesas = c.get(f"/disponibilidad?fecha={manana}&hora=20:00", headers=h_cliente).json()
        if mesas:
            break
    sufijo = uuid.uuid4().hex[:6]
    paso("HU-10 Registro de menor de edad rechazado (403)", c.post("/usuarios/registro", json={
        "nombre": "Menor Demo", "usuario": f"menor{sufijo}", "password": "Clave12345",
        "documento": "1234567", "fecha_nacimiento": "2015-01-01"}), 403)

    paso("HU-01 Disponibilidad 20:00", c.get(f"/disponibilidad?fecha={manana}&hora=20:00", headers=h_cliente), 200)
    mesa = mesas[0]["id"]
    reserva = paso(f"HU-02 Reserva de la mesa {mesa}", c.post("/reservas", headers=h_cliente, json={"mesa_id": mesa, "fecha": manana, "hora": "20:00"}), 201)
    paso("HU-02 Doble reserva de la misma mesa (409)", c.post("/reservas", headers=h_gerente, json={"cliente_id": "cliente2", "mesa_id": mesa, "fecha": manana, "hora": "20:00"}), 409)
    paso("HU-03 Check-in (anfitrión)", c.post("/reservas/checkin", headers=h_anfitrion, json={"codigo_confirmacion": reserva["codigo_confirmacion"]}), 200)
    paso("HU-03 Check-in repetido (409)", c.post("/reservas/checkin", headers=h_anfitrion, json={"codigo_confirmacion": reserva["codigo_confirmacion"]}), 409)

    paso("HU-04 Caja acredita puntos ($120.000)", c.post("/fidelidad/acumular", headers=h_cajero, json={"cliente_id": "cliente1", "monto_gastado": 120000}), 200)
    paso("HU-05 Canje de bebida gratis", c.post("/fidelidad/canjear", headers=h_cliente, json={"beneficio": "bebida_gratis"}), 200)
    paso("HU-06 Recarga de billetera", c.post("/billetera/recarga", headers=h_cliente, json={"monto": 50000, "metodo_pago": "tarjeta"}), 200)
    paso("HU-07 Saldo e historial", c.get("/billetera/cliente1", headers=h_cliente), 200)
    paso("HU-08 Validación de saldo en caja", c.get("/billetera/validar?cliente_id=cliente1&monto_requerido=50000", headers=h_cajero), 200)
    paso("HU-12 Reporte CSV (gerente)", c.get("/billetera/reportes", headers=h_gerente), 200)
    paso("HU-09 Recordatorios de reservas próximas", c.post("/notificaciones/reservas-proximas?horas=48", headers=h_anfitrion), 200)
    paso("HU-09 Notificaciones del cliente", c.get("/notificaciones/cliente1", headers=h_cliente), 200)

    paso("HU-11 Límite diario $50.000", c.post("/fidelidad/limite", headers=h_cliente, json={"limite_diario": 50000}), 200)
    r = paso("HU-11 Gasto $30.000 permitido", c.post("/fidelidad/gasto", headers=h_cliente, json={"monto": 30000}), 200)
    r = paso("HU-11 Gasto $30.000 rechazado por límite", c.post("/fidelidad/gasto", headers=h_cliente, json={"monto": 30000}), 200)
    if r and r.get("permitido") is not False:
        fallos.append("El segundo gasto debía ser rechazado")

    # Autoexclusión con un cliente nuevo para no bloquear a los usuarios de ejemplo.
    reg = {"nombre": "Cliente Demo", "usuario": f"demo{sufijo}", "password": "Clave12345",
           "documento": str(int(uuid.uuid4().int % 9_000_000_000) + 1_000_000_000), "fecha_nacimiento": "1995-05-05"}
    paso("HU-10 Registro de mayor de edad", c.post("/usuarios/registro", json=reg), 201)
    h_nuevo = {"Authorization": "Bearer " + c.post("/auth/login", json={"usuario": reg["usuario"], "password": reg["password"]}).json()["access_token"]}
    paso("HU-11 Autoexclusión 30 días", c.post("/fidelidad/autoexclusion", headers=h_nuevo, json={"dias": 30}), 200)
    paso("HU-11 Recarga bloqueada por autoexclusión (403)", c.post("/billetera/recarga", headers=h_nuevo, json={"monto": 1000, "metodo_pago": "tarjeta"}), 403)

    for _ in range(5):
        c.post("/auth/login", json={"usuario": "demo-no-existe", "password": "x"})
    paso("REQ-NFUNC-003 Credenciales malas => 401", c.post("/auth/login", json={"usuario": "cliente2", "password": "mala"}), 401)

    if fallos:
        print("\nFALLOS:\n- " + "\n- ".join(fallos))
        sys.exit(1)
    print("\nDemo completada: todos los pasos respondieron como se esperaba.")


if __name__ == "__main__":
    main()
