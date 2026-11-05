# Guion para la defensa (15 minutos + 5 de preguntas)

Antes de entrar: `docker compose up -d --build` ya ejecutado y probado en el computador que se usará; iniciar sesión de ejemplo en dos pestañas (cliente y anfitrión) y tener abiertos el repositorio, el tablero y `docs/DIAGRAMAS_SECUENCIA.md`.

| Min | Qué mostrar | Qué decir |
|---|---|---|
| 0–1 | Pantalla de acceso | Qué es GoldenTable y qué problema resuelve (filas en caja, errores de conciliación, falta de visibilidad). |
| 1–3 | Tablero de GitHub Projects | Columnas, historias asignadas, iteraciones de dos semanas, backlog final en Done. Metodología: Planning, MoSCoW, releases. |
| 3–5 | Repositorio: ramas, PRs, commits, issues, Actions | Ramas `feature/*`, Conventional Commits con REQ-ID, PR con `Closes #N`, CI en verde, trazabilidad. |
| 5–8 | `docs/DIAGRAMAS_SECUENCIA.md` | Recorrer 2 diagramas (login y reserva): participantes, método y ruta en cada mensaje y el camino alterno de error (423/409). |
| 8–13 | **Demo en vivo** (ver abajo) | Cada flujo, con el requisito que implementa. |
| 13–15 | `README`, `openapi.yaml`, Docker | Un comando levanta todo; OpenAPI documentado; JWT; cobertura. |

## Demo (≈5 min)

1. **Cliente (`cliente1`)** — REQ-FUNC-001/002: las mesas ya aparecen; clic en *Reservar* → código de confirmación. Intentar reservar la misma mesa desde otra cuenta → 409.
2. **Anfitrión (`anfitrion`)** — REQ-FUNC-003: *Reservas del día* → *Check-in* de `DEMO0001` o del código recién generado → estado "En curso".
3. **Cajero (`cajero`)** — REQ-FUNC-004/008: registrar un consumo de $120.000 para `cliente1` (+120 puntos); validar saldo.
4. **Cliente** — REQ-FUNC-005/006/007: canjear *Bebida gratis* (cupón), recargar $50.000 y ver el historial.
5. **Juego responsable** — REQ-FUNC-011: definir un límite de $50.000 y registrar dos gastos de $30.000 (el segundo se rechaza).
6. **Gerente (`gerente`)** — REQ-FUNC-012: *Reportes* → ver y descargar el CSV.
7. **JWT** — cerrar sesión (el token se borra); en `http://localhost:8000/docs` probar una ruta sin token → 401.

## Preguntas probables

- **¿Por qué FastAPI y PostgreSQL?** FastAPI genera OpenAPI y valida con Pydantic; PostgreSQL da integridad (restricción única contra reservas dobles) y transacciones.
- **¿Cómo evitan reservar dos veces la misma mesa?** Restricción única `(mesa, fecha, hora)` en la base de datos; la API responde 409.
- **¿Cómo funciona el bloqueo tras 5 intentos?** Contador en la tabla de usuarios; al quinto fallo se bloquea 15 minutos (423).
- **¿Quién puede hacer qué?** Roles cliente, anfitrión, cajero y gerente verificados por el API a partir del JWT; un cliente solo opera sobre su propia cuenta.
- **¿Qué falta?** Ver `docs/DEUDA_TECNICA.md`: push real, cifrado en reposo/TLS, pasarela de pagos.
- **¿Cómo prueban?** Pruebas con pytest contra PostgreSQL real y CI que levanta Docker Compose desde cero.
