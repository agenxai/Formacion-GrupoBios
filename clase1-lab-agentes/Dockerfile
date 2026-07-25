# =============================================================================
#  Imagen única para los dos servicios del compose: tablero y notebook.
#
#  Un solo paquete `backend/` compartido (spec 02): el notebook importa
#  exactamente los mismos módulos que corren detrás del tablero. Si el notebook
#  funciona, el tablero funciona.
#
#  La base de datos se genera EN EL BUILD, así que arrancar el laboratorio no
#  requiere red para los datos (spec 09, Riesgo 2).
# =============================================================================

FROM python:3.12-slim

# Sin .pyc, salida sin buffer (los logs se ven en vivo en `docker compose up`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Las dependencias primero: cambiar código no invalida esta capa.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación.
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY notebook/ ./notebook/
COPY scripts/ ./scripts/

# Base de datos sintética, determinista (ADR-005). La autocomprobación del seed
# FALLA EL BUILD si alguna de las cuatro anomalías o alguno de los
# identificadores de demo no quedó en la base: es preferible que la imagen no se
# construya a descubrirlo en el minuto 12 de la clase.
#
# `MODO=replay` durante el build para que config.py no exija la key, que no debe
# entrar a la imagen (spec 09, Riesgo 5).
RUN MODO=replay python -m backend.db.seed --recrear

# El usuario no privilegiado va después del seed para que la base quede legible
# pero el proceso no corra como root.
RUN useradd --create-home --uid 10001 lab && chown -R lab:lab /app
USER lab

EXPOSE 8000 8888

# El comando real lo define docker-compose.yml por servicio. Este default deja la
# imagen utilizable con `docker run` a secas.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
