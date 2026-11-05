"""
Configuración de la aplicación, leída de variables de entorno.

Los valores por defecto sirven para desarrollo local y coinciden con los
que declara compose.yaml (ver README, sección "Variables de entorno").
"""

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://goldentable:goldentable@localhost:5432/goldentable",
)

# Clave con la que se firman los tokens JWT (HS256). Cámbiala en producción.
JWT_SECRET = os.getenv("JWT_SECRET", "goldentable-dev-secret-cambiar-en-produccion")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# REQ-NFUNC-003: la cuenta se bloquea tras 5 intentos fallidos de inicio de sesión.
MAX_INTENTOS_LOGIN = 5
MINUTOS_BLOQUEO = int(os.getenv("MINUTOS_BLOQUEO", "15"))

# Si es "true", al arrancar se crean los usuarios y datos de ejemplo del README.
SEED_DATA = os.getenv("SEED_DATA", "true").lower() == "true"
