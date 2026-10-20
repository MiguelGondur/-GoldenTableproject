# Matriz de trazabilidad

Requisito (SRS) → Historia de usuario → Issue → Código → Pruebas → PR.

| Requisito | HU | Issue | Código | Pruebas | PR |
|---|---|---|---|---|---|
| REQ-FUNC-001 Disponibilidad | HU-01 | #1 | `src/api/main.py`, `store.py` | `test_disponibilidad.py`, `test_reservas.py` | #14 |
| REQ-FUNC-002 Reserva | HU-02 | #2 | `routers/reservas.py` | `test_reservas.py` | PR de reservas/check-in |
| REQ-FUNC-003 Check-in | HU-03 | #3 | `routers/reservas.py` | `test_checkin.py` | PR de reservas/check-in |
| REQ-FUNC-004 Acumulación | HU-04 | #4 | `routers/fidelidad.py` | `test_acumulacion.py`, `test_fidelidad.py` | #17, #19 |
| REQ-FUNC-005 Canje | HU-05 | #5 | `routers/fidelidad.py` | `test_fidelidad.py` | #17 |
| REQ-FUNC-006 Recarga | HU-06 | #6 | `routers/billetera.py` | `test_billetera.py` | #15 |
| REQ-FUNC-007 Validación de saldo | HU-07 | #7 | `routers/billetera.py` | `test_billetera.py` | #17 |
| REQ-FUNC-008 Reportes | HU-08 | #8 | `routers/billetera.py` | `test_billetera.py` | #17 |
| REQ-FUNC-009 Notificaciones | HU-09 | #9 | `routers/notificaciones.py` | `test_notificaciones.py` | PR de notificaciones |
| REQ-FUNC-010 Edad/identidad | HU-10 | #10 | `routers/usuarios.py` | `test_usuarios.py`, `test_usuarios_documento.py` | #16 |
| REQ-FUNC-011 Autoexclusión y límites | HU-11 | #11 | `routers/fidelidad.py`, `seguridad.py` | `test_autoexclusion.py`, `test_fidelidad.py` | #17, #19 |
| REQ-FUNC-012 Historial | HU-12 | #12 | `routers/billetera.py` | `test_billetera.py` | #17 |
| REQ-NFUNC-006 Cobertura > 80 % | — | — | `.github/workflows/ci.yml` | pytest-cov (`--cov-fail-under=80`) | PR de CI |

Nota: completar en la tabla los números reales de los PRs nuevos una vez creados.
