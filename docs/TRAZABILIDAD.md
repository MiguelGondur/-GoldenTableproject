# Matriz de trazabilidad

Requisito del SRS → Historia de usuario → Issue → Código → Pruebas → Pull Request.
(La numeración REQ-FUNC-00N corresponde a la historia US-00N del SRS y al issue #N del repositorio.)

| Requisito | Historia / Issue | Código | Pruebas | PR |
|---|---|---|---|---|
| REQ-FUNC-001 Consulta de disponibilidad | US-001 · #1 | `main.py` (`/disponibilidad`), `store.py` | `test_disponibilidad.py` | #14, #25 |
| REQ-FUNC-002 Reserva de mesa | US-002 · #2 | `routers/reservas.py` | `test_reservas.py` | #21, #25 |
| REQ-FUNC-003 Check-in de reserva | US-003 · #3 | `routers/reservas.py` | `test_checkin.py` | #21, #25 |
| REQ-FUNC-004 Acumulación de puntos | US-004 · #4 | `routers/fidelidad.py` | `test_fidelidad.py`, `test_acumulacion.py` | #17, #19, #20, #25 |
| REQ-FUNC-005 Canje de puntos | US-005 · #5 | `routers/fidelidad.py` | `test_fidelidad.py` | #17, #20, #25 |
| REQ-FUNC-006 Recarga de saldo | US-006 · #6 | `routers/billetera.py` | `test_billetera.py` | #15, #25 |
| REQ-FUNC-007 Consulta de saldo e historial | US-007 · #7 | `routers/billetera.py` | `test_billetera.py` | #17, #25 |
| REQ-FUNC-008 Validación de saldo en caja | US-008 · #8 | `routers/billetera.py` (`/validar`) | `test_billetera.py` | #17, #25 |
| REQ-FUNC-009 Notificaciones | US-009 · #9 | `routers/notificaciones.py` | `test_notificaciones.py` | #22, #25 |
| REQ-FUNC-010 Verificación de edad/identidad | US-010 · #10 | `routers/usuarios.py` | `test_usuarios.py`, `test_usuarios_documento.py` | #16, #20, #25 |
| REQ-FUNC-011 Límites de autoexclusión | US-011 · #11 | `routers/fidelidad.py`, `seguridad.py` | `test_autoexclusion.py`, `test_fidelidad.py` | #17, #19, #20, #25 |
| REQ-FUNC-012 Reportes de transacciones | US-012 · #12 | `routers/billetera.py` (`/reportes`) | `test_billetera.py` | #17, #25 |
| REQ-NFUNC-001 Disponibilidad < 2 s | — | `store.py` (consulta indexada) | `test_disponibilidad.py` (tiempo) | #25 |
| REQ-NFUNC-003 Bloqueo tras 5 intentos | — | `routers/auth.py` | `test_auth.py` | #25 |
| REQ-NFUNC-004 Reserva en ≤ 4 clics | — | `frontend/public/app.js` | prueba manual / e2e (ver abajo) | #25 |
| REQ-NFUNC-006 Cobertura > 80 % | — | `.github/workflows/ci.yml` | pytest-cov | #20, #25 |
| REQ-NFUNC-007 Navegadores y móviles | — | `frontend/public/styles.css` (responsive) | prueba manual en escritorio y móvil | #25 |

**REQ-NFUNC-004 (≤ 4 clics):** tras iniciar sesión, la pantalla de reservas ya muestra las mesas del día siguiente; reservar toma 1 clic (Reservar) o 3 si se cambia fecha y hora.

**Nota:** "#25" es el Pull Request que añade PostgreSQL, JWT, OpenAPI, Docker y el frontend; añade aquí su número (#N) una vez creado.
