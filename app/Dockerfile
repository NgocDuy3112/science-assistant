FROM python:3.12-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

RUN uv init .

RUN uv add -r requirements.txt

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]