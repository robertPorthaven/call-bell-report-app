# Use Debian 12 base (bookworm); 3.10 images are still published with this tag
FROM python:3.10-slim-bookworm

# OS deps for pyodbc + Azure SQL (modern keyring flow; no apt-key)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl gnupg2 ca-certificates apt-transport-https \
      build-essential \
      unixodbc unixodbc-dev \
 && mkdir -p /usr/share/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 # NOTE: pin the repo to Debian 12 (bookworm) explicitly
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
    https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

# (Optional) make /app importable explicitly
ENV PYTHONPATH=/app
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py obo_sql_client.py /app/
COPY assets/ /app/assets/
COPY .streamlit/ /app/.streamlit

# Non-root (optional)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]