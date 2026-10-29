FROM node:24-bookworm-slim AS dashboard
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright ADAPTIVE_QA_HOSTED_SANDBOX=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && python -m playwright install --with-deps chromium
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps . && groupadd -g 10001 qa && useradd -u 10001 -g qa -m qa && mkdir /data && chown qa:qa /data && chmod 700 /data
COPY --from=dashboard /build/dist/ /app/dashboard/
USER 10001:10001
WORKDIR /data
EXPOSE 8080
ENTRYPOINT ["python", "-m", "adaptive_qa"]
