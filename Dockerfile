# Minimal container image for reproducing the Python environment.
FROM python:3.10-slim

# Avoid interactive Debian prompts during package installation.
ENV DEBIAN_FRONTEND=noninteractive

# Install basic development tools used inside the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    nano \
    && rm -rf /var/lib/apt/lists/*

# All project commands run from /app inside the container.
WORKDIR /app
