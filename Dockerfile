FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home trader && mkdir -p /app/data /app/logs /app/artifacts && chown -R trader:trader /app
USER trader
EXPOSE 8000
CMD ["uvicorn", "quant_ai_trader.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

