# MapBiomas Fire Monitor — Sentinel-2
# Docker image for reproducible local execution
#
# Build:  docker build -t fire_monitor .
# Run:    docker-compose up
#
# Includes: Python 3.10, GDAL 3.6, rasterio, TensorFlow 2.13, JupyterLab

FROM python:3.10-slim-bullseye

LABEL maintainer="IPAM - wallace.silva@ipam.org.br"
LABEL description="MapBiomas Fire Monitor — Sentinel-2 Colab-compatible local environment"

# ── System dependencies (GDAL, gsutil, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    apt-transport-https \
    ca-certificates \
    gnupg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Google Cloud SDK (gsutil)
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
    https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# ── Set GDAL version for pip compatibility
ENV GDAL_VERSION=3.6.2
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# ── Python dependencies
WORKDIR /app
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install GDAL==${GDAL_VERSION} \
    && pip install --no-cache-dir -r requirements.txt

# ── JupyterLab extensions
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager 2>/dev/null || true

# ── Working directory
WORKDIR /workspace

# ── Expose JupyterLab port
EXPOSE 8888

# ── Default command: JupyterLab (no token for local use — bind to 0.0.0.0)
CMD ["jupyter", "lab", \
     "--ip=0.0.0.0", \
     "--port=8888", \
     "--no-browser", \
     "--NotebookApp.token=''", \
     "--NotebookApp.password=''", \
     "--allow-root"]
