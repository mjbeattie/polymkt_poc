FROM ubuntu:22.04

# Install Python 3.12
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-dev python3.12-venv python3-pip

# Core bash utilities
RUN apt-get install -y \
    bash bash-completion coreutils findutils util-linux procps \
    grep sed awk less nano vim

# Networking + DNS tools
RUN apt-get install -y \
    dnsutils iputils-ping traceroute curl wget net-tools iproute2

# Build tools
RUN apt-get install -y \
    build-essential

# Common utilities
RUN apt-get install -y \
    ca-certificates unzip tar

RUN rm -rf /var/lib/apt/lists/*
