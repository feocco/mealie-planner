FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY mealie_planner ./mealie_planner

RUN pip install --no-cache-dir .

VOLUME ["/app/data"]

EXPOSE 8080

CMD ["mealie-planner"]

