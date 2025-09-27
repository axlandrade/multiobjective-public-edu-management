# Use uma imagem oficial e leve do Python como base
FROM mcr.microsoft.com/devcontainers/python:3.11

# Defina o diretório de trabalho dentro do container
WORKDIR /workspace

# Copie o arquivo de dependências e instale-as
# Esta etapa é otimizada pelo cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- MELHORIA ---
# Copie todo o contexto do projeto (respeitando o .dockerignore)
COPY . .

# Dê permissão de execução para o script shell
RUN chmod +x run_experiments.sh

# Defina o comando padrão para abrir um terminal
CMD ["/bin/bash"]