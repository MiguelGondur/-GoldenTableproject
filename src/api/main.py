"""
GoldenTable API — punto de entrada de la aplicación.

Este es un esqueleto inicial (Seguimiento 1). Los endpoints reales para
cada requisito funcional (REQ-FUNC-001 a REQ-FUNC-012) se irán agregando
en las siguientes iteraciones, cada uno en su propia rama feature/*.
"""

from fastapi import FastAPI

app = FastAPI(
    title="GoldenTable API",
    description="API de reservas, fidelidad y billetera digital para casino físico.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Endpoint de salud básico para confirmar que la API está corriendo."""
    return {"status": "ok", "app": "GoldenTable"}


@app.get("/health")
def health_check():
    """Health check usado por el pipeline de CI en Seguimiento 3."""
    return {"status": "healthy"}
