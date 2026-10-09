FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
# config, dati e casi ambigui arrivano da volumi (vedi docker-compose.spesa.yml)
ENV PYTHONUNBUFFERED=1 TZ=Europe/Rome
RUN mkdir -p data review && chown -R nobody data review
USER nobody
CMD ["spesa-server"]
