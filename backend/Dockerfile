FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-huggingface.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-huggingface.txt -r requirements-production.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
