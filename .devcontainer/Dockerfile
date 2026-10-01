FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm

# Install networking tools and utilities
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        iputils-ping \
        net-tools \
        dnsutils \
        traceroute \
        curl \
        wget \
        git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
