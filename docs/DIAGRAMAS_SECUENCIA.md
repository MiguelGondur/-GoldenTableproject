# Diagramas de secuencia UML

Participantes reales del sistema: el **actor** (cliente, anfitrión, cajero o gerente), el **Frontend** (nginx + JavaScript), la **API** (FastAPI, que valida el JWT y los roles), la **capa de servicio** (la lógica de cada router: reglas de negocio) y la **base de datos** (PostgreSQL). Cada mensaje hacia la API indica método HTTP y ruta. El proveedor push es un servicio externo simulado (ver deuda técnica).

GitHub renderiza los bloques `mermaid` directamente.

## 1. Inicio de sesión con JWT y bloqueo tras 5 intentos (REQ-NFUNC-003) — con camino alterno de error

```mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de autenticación
    participant DB as PostgreSQL

    U->>F: Ingresa usuario y contraseña
    F->>A: POST /auth/login {usuario, password}
    A->>S: validar credenciales
    S->>DB: SELECT usuario, intentos_fallidos, bloqueado_hasta
    DB-->>S: fila del usuario
    alt cuenta bloqueada (bloqueado_hasta > ahora)
        S-->>A: bloqueada
        A-->>F: 423 Locked "Cuenta bloqueada"
        F-->>U: Muestra el aviso de bloqueo
    else contraseña incorrecta
        S->>DB: UPDATE intentos_fallidos + 1 (al 5.º: bloqueado_hasta = ahora + 15 min)
        A-->>F: 401 Unauthorized (o 423 si fue el 5.º intento)
        F-->>U: "Usuario o contraseña incorrectos"
    else credenciales válidas
        S->>DB: UPDATE intentos_fallidos = 0
        S-->>A: usuario y rol
        A-->>F: 200 OK {access_token, rol, nombre}
        F->>F: guarda el token (localStorage)
        F->>A: GET /auth/me (Authorization: Bearer token)
        A-->>F: 200 OK perfil
        F-->>U: Muestra la aplicación según el rol
    end
```

## 2. Reserva de mesa (REQ-FUNC-001 y REQ-FUNC-002) — con camino alterno de conflicto

```mermaid
sequenceDiagram
    actor C as Cliente
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de reservas
    participant DB as PostgreSQL

    C->>F: Abre Reservas (fecha y hora)
    F->>A: GET /disponibilidad?fecha=2026-11-10&hora=20:00 (Bearer token)
    A->>A: valida JWT
    A->>S: mesas libres
    S->>DB: SELECT mesas libres que no tengan reserva ese día y hora
    DB-->>S: mesas
    A-->>F: 200 OK [mesas]
    F-->>C: Muestra las mesas

    C->>F: Clic en "Reservar" (mesa 6)
    F->>A: POST /reservas {mesa_id, fecha, hora} (Bearer token)
    A->>A: valida JWT y rol, verifica autoexclusión
    A->>S: crear reserva
    S->>DB: INSERT reserva (restricción única mesa+fecha+hora)
    alt la mesa sigue libre
        DB-->>S: reserva creada
        A-->>F: 201 Created {codigo_confirmacion}
        F-->>C: Muestra el código de confirmación
    else otra persona la reservó antes
        DB-->>S: violación de la restricción única
        A-->>F: 409 Conflict "La mesa ya está reservada"
        F-->>C: Aviso y refresca las mesas
    else cliente autoexcluido
        A-->>F: 403 Forbidden "Cliente autoexcluido"
        F-->>C: Aviso de bloqueo
    end
```

## 3. Check-in del anfitrión (REQ-FUNC-003)

```mermaid
sequenceDiagram
    actor H as Anfitrión
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de reservas
    participant DB as PostgreSQL

    H->>F: Abre "Reservas del día"
    F->>A: GET /reservas?fecha=2026-11-10 (Bearer token)
    A->>A: valida JWT y rol anfitrion/gerente
    A->>S: listar
    S->>DB: SELECT reservas del día ORDER BY hora
    A-->>F: 200 OK [reservas]
    H->>F: Ingresa el código y pulsa Check-in
    F->>A: POST /reservas/checkin {codigo_confirmacion}
    A->>S: marcar en curso
    S->>DB: SELECT reserva FOR UPDATE
    alt código válido y confirmada
        S->>DB: UPDATE estado = en_curso, check_in_en = ahora
        A-->>F: 200 OK reserva en_curso
    else código inexistente
        A-->>F: 404 Not Found
    else ya se hizo check-in
        A-->>F: 409 Conflict
    else el usuario es cliente
        A-->>F: 403 Forbidden
    end
    F-->>H: Muestra el resultado
```

## 4. Consumo en caja, acumulación y canje de puntos (REQ-FUNC-004 y REQ-FUNC-005) — con camino alterno de puntos insuficientes

```mermaid
sequenceDiagram
    actor K as Cajero
    actor C as Cliente
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de fidelidad
    participant DB as PostgreSQL

    K->>F: Registra consumo de $120.000 de cliente1
    F->>A: POST /fidelidad/acumular {cliente_id, monto_gastado} (Bearer cajero)
    A->>A: valida JWT y rol cajero/gerente
    A->>S: acreditar (1 punto por $1.000)
    S->>DB: verifica autoexclusión, UPDATE puntos = puntos + 120 (FOR UPDATE)
    A-->>F: 200 OK {puntos_ganados: 120, puntos_totales}
    F-->>K: Confirmación

    C->>F: Elige "Bebida gratis"
    F->>A: POST /fidelidad/canjear {beneficio} (Bearer cliente)
    A->>S: canjear
    S->>DB: SELECT puntos FOR UPDATE
    alt puntos suficientes
        S->>DB: UPDATE puntos - costo, INSERT canje (cupón)
        A-->>F: 200 OK {cupon, puntos_restantes}
        F-->>C: Muestra el cupón digital
    else puntos insuficientes
        A-->>F: 402 Payment Required
        F-->>C: Aviso de puntos insuficientes
    else beneficio inexistente
        A-->>F: 404 Not Found
    end
```

## 5. Recarga de saldo y límite de gasto (REQ-FUNC-006, REQ-FUNC-011)

```mermaid
sequenceDiagram
    actor C as Cliente
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de billetera
    participant DB as PostgreSQL

    C->>F: Recarga $50.000 con tarjeta
    F->>A: POST /billetera/recarga {monto, metodo_pago} (Bearer cliente)
    A->>S: recargar
    S->>DB: verifica autoexclusión, UPDATE saldo (FOR UPDATE), INSERT transacción
    alt monto válido y cliente activo
        A-->>F: 200 OK {saldo}
    else monto <= 0 o medio de pago inválido
        A-->>F: 422 Unprocessable Entity
    else cliente autoexcluido
        A-->>F: 403 Forbidden
    end
    F->>A: GET /billetera/cliente1 (Bearer cliente)
    A-->>F: 200 OK {saldo, últimas 20 transacciones}

    C->>F: Registra un gasto de $30.000
    F->>A: POST /fidelidad/gasto {monto}
    A->>S: validar límite diario
    S->>DB: SELECT limite y gasto de hoy
    alt gasto + hoy <= límite
        S->>DB: UPDATE gasto de hoy
        A-->>F: 200 OK {permitido: true}
    else supera el límite
        A-->>F: 200 OK {permitido: false} (no se registra)
    end
```

## 6. Notificaciones push (REQ-FUNC-009)

```mermaid
sequenceDiagram
    actor H as Anfitrión
    actor C as Cliente
    participant F as Frontend (nginx + JS)
    participant A as API (FastAPI)
    participant S as Servicio de notificaciones
    participant DB as PostgreSQL
    participant P as Proveedor push (simulado)

    H->>F: Pulsa "Enviar recordatorios" (próximas 2 h)
    F->>A: POST /notificaciones/reservas-proximas?horas=2 (Bearer anfitrión)
    A->>S: buscar reservas próximas
    S->>DB: SELECT reservas confirmadas sin recordatorio en la ventana
    loop por cada reserva
        S->>DB: INSERT notificación, UPDATE recordatorio_enviado = true
        S->>P: push al cliente (registro en el log)
    end
    A-->>F: 200 OK [notificaciones enviadas]

    C->>F: Abre Notificaciones
    F->>A: GET /notificaciones/cliente1 (Bearer cliente)
    A->>DB: SELECT notificaciones ORDER BY id DESC
    A-->>F: 200 OK [notificaciones]
    F-->>C: Lista de avisos
```
