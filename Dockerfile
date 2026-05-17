# Runtime image for the Streamlit dashboard and command-line experiments.
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# git is useful for devcontainers; curl supports the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so Docker can reuse this layer when code changes.
COPY requirements.txt setup.py ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "gui/dashboard_web.py"]
