# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

# Install packages.
#
# Alphabetic ordering is recommended.
RUN apt-get update && \
    apt-get install -y automake \
                       autotools-dev \
                       build-essential \
                       curl \
                       gawk \
                       gcc-arm-none-eabi \
                       git \
                       libclang-dev \
                       libffi-dev \
                       libssl-dev \
                       libtool \
                       pkg-config \
                       pycodestyle \
                       python3 \
                       python3-pip \
                       reuse && \
    rm -rf /var/lib/apt/lists/*

# Install rustup.
ENV RUSTUP_HOME="/rustup"
ENV CARGO_HOME="/cargo"
RUN mkdir -p /rustup /cargo && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
        sh -s -- -y --profile minimal --default-toolchain 1.77.1
ENV PATH="/cargo/bin:${PATH}"

# Finish installation of Rust toolchain.
RUN rustup component add clippy && \
    rustup component add rustfmt && \
    rustup target add thumbv7em-none-eabihf

# Install binaries using cargo.
RUN cargo install bindgen-cli@^0.69.5 --locked && \
    mv /cargo/bin/bindgen /usr/local/bin/bindgen && \
    chmod 755 /usr/local/bin/bindgen

RUN cargo install cbindgen@^0.24 --locked && \
    mv /cargo/bin/cbindgen /usr/local/bin/cbindgen && \
    chmod 755 /usr/local/bin/cbindgen

RUN cargo install just@1.23.0 --locked && \
    mv /cargo/bin/just /usr/local/bin/just && \
    chmod 755 /usr/local/bin/just

# Allow all users to use CARGO_HOME and RUSTUP_HOME.
RUN chmod -R 777 /cargo && \
    chmod -R 777 /rustup
