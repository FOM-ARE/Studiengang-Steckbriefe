# ─── Build Stage ───
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ─── Runtime Stage ───
FROM python:3.11-slim

WORKDIR /app

# ODBC Driver fuer SQL Server
# curl/gnupg2 nur fuer den Repo-Key; danach entfernt (zieht sonst libcurl4/libbrotli1 mit, CVE-2026-111497)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       curl gnupg2 unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get purge -y --auto-remove curl gnupg2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/
COPY wsgi.py .

# Non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8080

CMD ["python", "wsgi.py", "--production"]
