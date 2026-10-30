FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements-lock.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-lock.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements-lock.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements-lock.txt     && rm -rf /wheels && groupadd -g 10001 hub && useradd -u 10001 -g hub hub
COPY --chown=hub:hub . .
RUN mkdir -p media staticfiles && chown -R hub:hub media staticfiles
USER hub
RUN DEBUG=false SECRET_KEY=build-only-not-a-runtime-secret python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
