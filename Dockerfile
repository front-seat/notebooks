FROM python:3.13-slim-bookworm

# Also install node and npm (used to build the frontend)
# RUN apt-get update && \
#       apt-get install -y nodejs npm && \
#       rm -rf /var/lib/apt/lists/*

# Install Astral's UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install our project
ADD . /app
WORKDIR /app
RUN uv sync --dev --group analysis --frozen

# Open port 5000
EXPOSE 5000

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port", "5000"]