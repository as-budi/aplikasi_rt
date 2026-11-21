FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Library untuk meng-compile mysqlclient
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} app && useradd -m -u ${UID} -g app app

# --- Pengembangan: kode di-mount dari host ---
FROM base AS dev
USER app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Produksi: kode disalin ke image ---
FROM base AS prod
COPY --chown=app:app . .
RUN mkdir -p /app/media /app/staticfiles && chown app:app /app/media /app/staticfiles
USER app
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
