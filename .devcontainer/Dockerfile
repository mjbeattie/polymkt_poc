ARG VARIANT="3.12"
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

# Update package index
RUN apt-get update

# Core bash utilities
RUN apt-get install -y \
    bash \
    bash-completion \
    coreutils \
    findutils \
    util-linux \
    procps \
    grep \
    sed \
    awk \
    less \
    nano \
    vim

# Networking + DNS tools
RUN apt-get install -y \
    dnsutils \
    iputils-ping \
    traceroute \
    curl \
    wget \
    net-tools \
    iproute2

# Build tools for Python packages
RUN apt-get install -y \
    build-essential \
    python3-dev

# Common utilities needed for HTTPS and packaging
RUN apt-get install -y \
    ca-certificates \
    unzip \
    tar

# Clean up
RUN rm -rf /var/lib/apt/lists/*
