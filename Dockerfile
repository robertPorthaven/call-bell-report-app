FROM python:3.10-slim-bookworm

# OS deps for ODBC 18 + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl gnupg2 ca-certificates apt-transport-https \
      build-essential \
      unixodbc unixodbc-dev \
 && mkdir -p /usr/share/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
    https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY app.py      /app/
COPY config.py   /app/
COPY auth/       /app/auth/
COPY db/         /app/db/
COPY assets/     /app/assets/
COPY .streamlit/ /app/.streamlit/

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
