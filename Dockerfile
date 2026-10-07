# LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.
# For authorised, self-hosted security training only.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Unprivileged user with a fixed UID/GID (predictable for volume mounts / k8s runAsUser)
RUN groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --no-create-home \
             --home-dir /app --shell /usr/sbin/nologin app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Files owned by the app user so the app can read them (and write if it needs to)
COPY --chown=app:app . .

EXPOSE 5000

USER app:app

# single worker keeps the in-memory progress/scoreboard consistent
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "app:app"]
