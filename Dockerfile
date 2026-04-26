# Usa uma imagem oficial do Python
FROM python:3.10-slim

# Instala ferramentas básicas necessárias para pacotes C e compilação
RUN apt-get update && apt-get install -y gcc g++ libc-dev && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho
WORKDIR /app

# Primeiro copiamos apenas os requisitos para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Mantém o contêiner vivo para podermos entrar nele depois
CMD ["tail", "-f", "/dev/null"]