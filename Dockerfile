# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

# Install packages.
#
# Alphabetic ordering is recommended.
RUN apt-get update && \
    apt-get install -y automake \
                       autotools-dev \
                       build-essential \
                       curl \
                       gcc-arm-none-eabi \
                       git \
                       libffi-dev \
                       libssl-dev \
                       libtool \
                       pkg-config \
                       pycodestyle \
                       python3 \
                       python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install reuse.
RUN pip3 install reuse

# Install rustup.
ENV RUSTUP_HOME="/rustup"
ENV CARGO_HOME="/cargo"
RUN mkdir -p /rustup /cargo && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
        sh -s -- -y --profile minimal --default-toolchain 1.70.0
ENV PATH="/cargo/bin:${PATH}"

# Finish installation of Rust toolchain.
RUN rustup component add clippy && \
    rustup component add rustfmt && \
    rustup target add thumbv7em-none-eabihf

# Install binaries using cargo.
RUN cargo install cbindgen@^0.24 && \
    cargo install just@^1.13 && \
    mv /cargo/bin/cbindgen /usr/local/bin/cbindgen && \
    mv /cargo/bin/just /usr/local/bin/just && \
    chmod 755 /usr/local/bin/cbindgen && \
    chmod 755 /usr/local/bin/just

# Allow all users to use CARGO_HOME and RUSTUP_HOME.
RUN chmod -R 777 /cargo && \
    chmod -R 777 /rustup
