# PLATFORMA calculator backend — FastAPI + WeasyPrint (PDF).
#
# WeasyPrint требует системные библиотеки рендеринга (Pango/Cairo/GDK-Pixbuf),
# которых нет в стандартном Python-buildpack на Render/Railway — поэтому
# используем полноценный Docker-образ, а не "просто Python service".

FROM python:3.12-slim

# Системные зависимости WeasyPrint.
# (libgdk-pixbuf2.0-0 в Debian trixie переименован в libgdk-pixbuf-2.0-0 —
#  оставляем оба варианта через `|| apt-get install -y libgdk-pixbuf-2.0-0`,
#  чтобы сборка не падала при обновлении базового образа.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
    || (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 \
        libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libffi8 \
        shared-mime-info fonts-dejavu-core) \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite-файл платформы — на Render/Railway диск эфемерный между деплоями
# (если не подключен persistent disk), поэтому при каждом старте контейнера
# накатываем seed заново, это дёшево и идемпотентно (см. scripts/seed_db.py).
# Если данные важно копить между деплоями (реальные заявки, quotes) —
# подключите persistent volume на /app и уберите seed из ENTRYPOINT, либо
# перейдите на Postgres (DATABASE_URL уже читается через переменную окружения
# в app/database.py — потребуется небольшая правка под psycopg2).
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed_db.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
