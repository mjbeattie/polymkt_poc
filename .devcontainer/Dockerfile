ARG VARIANT="3"
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

# Git + Git LFS
RUN apt-get install -y \
    git \
    git-lfs

# Python build utilities
RUN apt-get install -y \
    build-essential \
    python3-dev \
    python3-venv

# Clean up
RUN rm -rf /var/lib/apt/lists/*
