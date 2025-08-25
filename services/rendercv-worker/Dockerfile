# services/rendercv-worker/Dockerfile
FROM python:3.12-slim

# Install LaTeX bits needed by RenderCV (lean set)
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    latexmk texlive-xetex texlive-latex-extra texlive-fonts-recommended \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps from this folder
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app code
COPY main.py /app/main.py

# Render provides PORT; uvicorn must listen on it
ENV PORT=8080
CMD ["bash", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
