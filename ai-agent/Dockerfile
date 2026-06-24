FROM python:3.11-slim

WORKDIR /workspace
COPY workspace/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workspace /workspace

CMD ["python3", "src/discord_agent.py"]
