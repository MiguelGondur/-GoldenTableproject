# Deuda técnica y limitaciones conocidas

- **Persistencia:** todos los datos viven en memoria (`src/api/store.py` y módulos de routers); se pierden al reiniciar. Falta integrar una base de datos (p. ej. PostgreSQL).
- **Autenticación/seguridad (REQ-NFUNC-003):** no hay autenticación ni bloqueo por intentos fallidos; `cliente_id` se confía tal cual.
- **Cifrado (REQ-NFUNC-002):** sin cifrado de datos sensibles en reposo.
- **Notificaciones push:** el envío se simula con log; falta integrar FCM/APNs y un scheduler real para `/notificaciones/reservas-proximas`.
- **Vencimiento de puntos:** no existe modelo de caducidad; solo se puede enviar el aviso manualmente.
- **Clientes:** no hay apps móvil ni panel de administración; solo API.
- **Concurrencia:** la reserva de mesas no es atómica ante peticiones simultáneas.
- **Zonas horarias:** fechas y horas se tratan como hora local sin zona.
- **Requisitos no implementados:** REQ-NFUNC-004, 005 y 007.
