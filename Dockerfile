# Usa Python 3.13 Slim (Leve e estável)
FROM python:3.13-slim

# Evita arquivos .pyc e logs presos no buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema (necessário para alguns pacotes Python)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia os requirements
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto
COPY . .

# Exposição de portas (Documentação apenas, o Compose que define)
EXPOSE 8501

# Comando padrão (será sobrescrito pelo docker-compose)
CMD ["streamlit", "run", "main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
