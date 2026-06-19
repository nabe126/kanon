FROM python:3.11-slim

# Docker CLI をインストールするためのパッケージ追加
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
    && echo "deb [arch=amd64] https://download.docker.com/linux/debian buster stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
