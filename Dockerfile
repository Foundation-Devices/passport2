# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

FROM ubuntu:20.04 AS cross_build
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y git make gcc-arm-none-eabi python3 gcc && \
    rm -rf /var/lib/apt/lists/*
COPY drivers /workspace/passport-air/drivers
COPY docs /workspace/passport-air/docs
COPY extmod /workspace/passport-air/extmod
COPY lib /workspace/passport-air/lib
COPY mpy-cross /workspace/passport-air/mpy-cross
COPY py /workspace/passport-air/py
COPY ports/stm32/boards/Passport/include /workspace/passport-air/ports/stm32/boards/Passport/include
COPY ports/stm32/boards/Passport/common /workspace/passport-air/ports/stm32/boards/Passport/common
COPY ports/stm32/boards/Passport/images /workspace/passport-air/ports/stm32/boards/Passport/images
WORKDIR /workspace/passport-air/mpy-cross
RUN make

FROM ubuntu:20.04 AS cosign_build
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace
RUN apt-get update && \
    apt-get install -y git make libssl-dev gcc && \
    rm -rf /var/lib/apt/lists/*
COPY ports/stm32/boards/Passport/tools/cosign /workspace/passport-air/ports/stm32/boards/Passport/tools/cosign
COPY ports/stm32/boards/Passport/include /workspace/passport-air/ports/stm32/boards/Passport/include
COPY ports/stm32/boards/Passport/common /workspace/passport-air/ports/stm32/boards/Passport/common
COPY lib /workspace/passport-air/lib
WORKDIR /workspace/passport-air/ports/stm32/boards/Passport/tools/cosign
RUN make

FROM ubuntu:20.04 AS firmware_builder
ARG DEBIAN_FRONTEND=noninteractive
COPY --from=cosign_build \
    /workspace/passport-air/ports/stm32/boards/Passport/tools/cosign/x86/release/cosign /usr/bin/cosign
COPY --from=cross_build \
    /workspace/passport-air/mpy-cross/mpy-cross /usr/bin/mpy-cross
ENV PATH="${PATH}:~/bin"
RUN apt-get update && \
    apt-get install -y make gcc-arm-none-eabi autotools-dev automake libtool python3 curl libffi-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
