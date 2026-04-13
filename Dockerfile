FROM python:3.10 
 
WORKDIR /app 
 
COPY . . 
 
RUN pip install --no-cache-dir -r requirements.txt 
 
ENV PYTHONPATH=/app 
ENV SENTIENTSHIELD_LIGHT_MODE=true 
ENV THREAT_INGEST_PUBLIC_FALLBACK=true 
ENV THREAT_INGEST_INTERVAL_SECONDS=60 
 
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
