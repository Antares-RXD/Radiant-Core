# Dockerfile for Radiant Core with wallet support
# Multi-stage build for smaller final image
# Builds from GitHub repository for reproducible builds

# Stage 1: Build
FROM ubuntu:22.04 AS builder

ARG GIT_TAG=main
ARG BUILD_TYPE=Release
ARG BUILD_RADIANT_WALLET=ON
ARG BUILD_RADIANT_ZMQ=ON

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libboost-all-dev \
    libevent-dev \
    libssl-dev \
    libdb++-dev \
    libminiupnpc-dev \
    libzmq3-dev \
    libqrencode-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Clone from GitHub repository
RUN git clone --depth 1 --branch ${GIT_TAG} https://github.com/Radiant-Core/Radiant-Core.git radiant-core

WORKDIR /build/radiant-core

# Build with wallet support (skip man pages)
RUN mkdir -p build && cd build && \
    cmake \
        -DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
        -DBUILD_RADIANT_WALLET=${BUILD_RADIANT_WALLET} \
        -DBUILD_RADIANT_DAEMON=ON \
        -DBUILD_RADIANT_CLI=ON \
        -DBUILD_RADIANT_TX=ON \
        -DBUILD_RADIANT_ZMQ=${BUILD_RADIANT_ZMQ} \
        -DBUILD_RADIANT_QT=OFF \
        -DBUILD_RADIANT_SEEDER=OFF \
        -DENABLE_HARDENING=ON \
        -DENABLE_UPNP=ON \
        .. && \
    make -j$(nproc) radiantd radiant-cli radiant-tx

# Strip binaries
RUN strip /build/radiant-core/build/src/radiantd \
    /build/radiant-core/build/src/radiant-cli \
    /build/radiant-core/build/src/radiant-tx

# Stage 2: Runtime
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libboost-chrono1.74.0 \
    libboost-filesystem1.74.0 \
    libboost-thread1.74.0 \
    libevent-2.1-7 \
    libevent-pthreads-2.1-7 \
    libssl3 \
    libdb5.3++ \
    libminiupnpc17 \
    libzmq5 \
    && rm -rf /var/lib/apt/lists/*

# Create radiant user
RUN useradd -m -s /bin/bash radiant

# Copy binaries from builder
COPY --from=builder /build/radiant-core/build/src/radiantd /usr/local/bin/
COPY --from=builder /build/radiant-core/build/src/radiant-cli /usr/local/bin/
COPY --from=builder /build/radiant-core/build/src/radiant-tx /usr/local/bin/

# Create data directory
RUN mkdir -p /home/radiant/.radiant && \
    chown -R radiant:radiant /home/radiant/.radiant

# Switch to radiant user
USER radiant
WORKDIR /home/radiant

# Expose ports (mainnet)
EXPOSE 7332 7333

# Expose ports (testnet)
EXPOSE 27332 27333

# Default command - run with server and wallet enabled
CMD ["radiantd", "-server=1", "-txindex=1", "-disablewallet=0", "-printtoconsole"]
