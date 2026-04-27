FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    nano \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app