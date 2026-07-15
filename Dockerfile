# LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.
# For authorised, self-hosted security training only.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
# single worker keeps the in-memory progress/scoreboard consistent
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "app:app"]
