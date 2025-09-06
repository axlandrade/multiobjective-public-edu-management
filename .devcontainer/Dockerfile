# Use uma imagem oficial e leve do Python como base
FROM python:3.12-slim

# Defina o diretório de trabalho dentro do container
WORKDIR /workspace

# Copie o arquivo de dependências e instale-as
# Esta etapa é otimizada pelo cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o código-fonte da sua aplicação para o container
COPY ./src ./src

# Copie os scripts de execução
COPY run_experiments.sh .
# Dê permissão de execução para o script shell
RUN chmod +x run_experiments.sh

# Defina o comando padrão para abrir um terminal
CMD ["/bin/bash"]