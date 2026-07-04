FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# data/ (bar cache) and the SQLite file live on a volume — see docker-compose.yml
CMD ["python", "-m", "src.trading", "backtest", "--symbol", "RELIANCE.NS"]
