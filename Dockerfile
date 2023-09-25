# temp stage
FROM python:3.11.4-slim-buster as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# final stage
FROM python:3.11.4-slim-buster

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# TODO: Cache Python Packages to the Docker Host
# TODO: ENTRYPOINT 
# TODO: only COPY what is needed
# TODO: HEALTHCHECK CMD curl --fail http://localhost:8000 || exit 1
# TODO: add a health check to a Docker Compose file
# TODO: add envars via --mount=type=secret
# TODO: use gunicorn --worker-tmp-dir /dev/shm config.wsgi -b 0.0.0.0:8000
# TODO: update dockerfile.json snippet
# TODO: use docker scan before deployment

COPY . .

RUN addgroup --gid 1001 --system app && \
    adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --group app

USER app