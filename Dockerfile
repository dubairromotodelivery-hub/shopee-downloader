FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

# Expõe a porta que a aplicação vai rodar
EXPOSE 8000

# Variável de ambiente para a porta
ENV PORT=8000

# Executa o servidor FastAPI com Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
