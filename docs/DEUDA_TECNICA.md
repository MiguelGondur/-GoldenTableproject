# Deuda técnica y limitaciones conocidas

Superado en la entrega final (ya no es deuda): persistencia en memoria → PostgreSQL; autenticación y bloqueo por intentos fallidos (REQ-NFUNC-003) → JWT con roles; reservas no atómicas → restricción única en base de datos.

Pendiente:

- **Cifrado (REQ-NFUNC-002):** las contraseñas se guardan con PBKDF2-HMAC-SHA256 con sal, pero no hay cifrado AES-256 de datos en reposo ni TLS 1.3 (el sistema corre en HTTP local; en producción iría detrás de un proxy con HTTPS).
- **Notificaciones push:** el envío se simula (registro en base de datos y log). Falta integrar FCM/APNs y un scheduler real para `/notificaciones/reservas-proximas` (hoy lo dispara el personal).
- **Vencimiento de puntos:** no hay modelo de caducidad; solo se puede enviar el aviso manualmente.
- **Pagos:** la recarga acepta el medio de pago como dato (`tarjeta`, `pse`, `efectivo`) sin pasarela de pago real.
- **Migraciones:** las tablas se crean con `create_all` al arrancar; falta una herramienta de migraciones (Alembic).
- **Administración de usuarios:** el personal solo existe como datos de ejemplo; no hay pantalla para crearlo. El registro público crea únicamente clientes.
- **Cliente móvil nativo:** la aplicación es web responsive (REQ-NFUNC-007 se cubre con navegador móvil).
- **Disponibilidad 99,5 % (REQ-NFUNC-005):** sin monitoreo ni alta disponibilidad.
- **Secretos:** `JWT_SECRET` y credenciales de la base tienen valores por defecto solo aptos para desarrollo.
