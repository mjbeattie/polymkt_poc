ARG VARIANT="3"
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

RUN apt-get update \
 && apt-get install -y dnsutils iputils-ping traceroute curl \
 && rm -rf /var/lib/apt/lists/*