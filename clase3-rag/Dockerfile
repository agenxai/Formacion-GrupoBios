# Dockerfile del tablero de la Clase 3 · RAG.
# Servidor FastAPI + frontend estático en el mismo proceso.
# El servicio Chroma (n8n/servicio_rag.py) NO va aquí — lo aloja TI de Bios.

FROM python:3.12-slim

WORKDIR /app

# Dependencias primero (cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo del backend
COPY app/ ./app/

# Frontend self-contained — el artefacto curado por el usuario.
COPY rag-class.html ./rag-class.html

# Data pre-bakeada incluida en el repo (se monta como volume en compose).
COPY app/data/ /app/app/data/

# Scripts de validación (para correrlos dentro del container si se quiere).
COPY scripts/validar_contraste.py scripts/auditar_visual.py scripts/verificar_vendor.py ./scripts/

# Assets (logo Bios, sources woff2…). Opcional.
COPY app/frontend/assets/ /app/app/frontend/assets/

ENV PYTHONUNBUFFERED=1
ENV PUERTO_TABLERO=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]