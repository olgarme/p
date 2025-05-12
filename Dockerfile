# setup
FROM python:3.11.5

WORKDIR /app

# Copy all necessary files
COPY requirements.txt /app/
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY examples/ /app/examples/

# Install dependencies
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install build
RUN python -m build .
RUN pip3 install .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    ca-certificates \
    libasound2 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install OpenSSL
RUN wget -O - https://www.openssl.org/source/openssl-1.1.1w.tar.gz | tar zxf - \
    && cd openssl-1.1.1w \
    && ./config --prefix=/usr/local \
    && make -j $(nproc) \
    && make install_sw install_ssldirs \
    && ldconfig -v \
    && cd .. \
    && rm -rf openssl-1.1.1w

ENV SSL_CERT_DIR=/etc/ssl/certs
ENV PYTHONUNBUFFERED=1

# Set working directory to phone-chatbot
WORKDIR /app/examples/phone-chatbot

# List contents for debugging
RUN ls -la

EXPOSE 8000

# Run the application
CMD ["gunicorn", "--workers=2", "--log-level", "debug", "--capture-output", "app:app", "--bind=0.0.0.0:8000"]
