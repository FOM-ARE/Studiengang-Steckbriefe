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
# Key-Download per Python statt curl/gnupg2: keine Hilfspakete, die spaeter per purge entfernt werden muessten
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends unixodbc-dev \
    && python -c "import urllib.request; urllib.request.urlretrieve('https://packages.microsoft.com/keys/microsoft.asc', '/usr/share/keyrings/microsoft-prod.asc')" \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.asc] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && (dpkg-query -W -f='${Package} ${Version}\n' 'libbrotli*' 'libcurl*' 2>/dev/null || true) \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Build abbrechen, wenn der ODBC-Treiber nicht ladbar ist (faellt sonst erst zur Laufzeit als 503 auf)
RUN odbcinst -q -d -n "ODBC Driver 17 for SQL Server" \
    && ls /opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.*.so* \
    && if ldd /opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.*.so* | grep "not found"; then exit 1; fi

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/
COPY wsgi.py .

# Non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8080

CMD ["python", "wsgi.py", "--production"]
