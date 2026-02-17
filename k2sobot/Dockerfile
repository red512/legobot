# Use official Python slim image
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system deps (curl only)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        file \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl (stable) - detect architecture with verification
RUN ARCH=$(dpkg --print-architecture) \
    && echo "Downloading kubectl for architecture: ${ARCH}" \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl" \
    && file kubectl \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl \
    && kubectl version --client \
    && echo "kubectl installed successfully"

# Install ArgoCD CLI - detect architecture with verification
RUN ARCH=$(dpkg --print-architecture) \
    && echo "Downloading ArgoCD for architecture: ${ARCH}" \
    && curl -sSL -o /usr/local/bin/argocd \
    https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-${ARCH} \
    && chmod +x /usr/local/bin/argocd \
    && /usr/local/bin/argocd version --client \
    && echo "ArgoCD installed successfully"

# copy requirements first for layer caching
COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# copy application code (dockerignore will exclude venv/.git)
COPY . .

# create a non-root user with home directory and set permissions
RUN groupadd -r k2sobot && useradd -r -g k2sobot -m -d /home/k2sobot k2sobot \
    && mkdir -p /app/logs \
    && chown -R k2sobot:k2sobot /app \
    && chown -R k2sobot:k2sobot /home/k2sobot

USER k2sobot

EXPOSE 3000

CMD ["python3", "main.py"]