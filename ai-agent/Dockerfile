FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    make \
    lsof \
    sudo \
    curl \
    && curl -fsSL https://get.docker.com | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY workspace /workspace
CMD ["python3", "src/discord_agent.py"]
