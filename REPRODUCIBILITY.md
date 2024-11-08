<!--
SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Reproducibility Guide

The instructions below describe how to easily build and verify Passport firmware in a reproducible way.

Please note that this guide has been designed for Linux, so if you’re running a different operating system the exact steps here may differ slightly. However, we’ve done our best to make them as portable as possible for other popular operating systems.

## What to Expect

In this guide we will outline the exact steps necessary to get set up, build firmware directly from the source code, and verify that it properly matches the published build hash and release binaries (minus signatures) for any given version of Passport’s firmware. Once you’ve completed the steps outlined here, you’ll have verified fully that the source code for a given version does indeed match the binaries we release to you. This ensures that nothing outside of the open-source code has been included in any given release, and that the released binaries are indeed built directly from the publicly available source code.

Security through transparency is the goal here, and firmware reproducibility is a key aspect of that!

Just want a taste of what to expect? Watch the entire process, start to finish, in this quick video:

[![asciicast](https://asciinema.org/a/5DtKQT0gH5LnYIpSHonOkkUif.svg)](https://asciinema.org/a/5DtKQT0gH5LnYIpSHonOkkUif)

## Setup

In order to build and verify the reproducibility of Passport firmware, you will need to:

- Get the source code
- Install the dependencies
    - [Docker](https://docs.docker.com/desktop/) or [Podman](https://podman.io/).
    - [Just](https://github.com/casey/just#installation)
- Build the reproducible binaries
- Verify the binaries match the:
    - Published build hash
    - Release binary (with signatures stripped out) hash

We’ll walk through every step above in this guide to ensure you can build and verify any version of Passport’s firmware easily.

### **Get the Source Code**

The instructions below assume you are installing into your home folder at `~/passport2`. You can choose to install to a different folder, and just update command paths appropriately.

Be sure to specify the correct version you want to reproduce here in the `git checkout` command, i.e., `v2.1.2`:

```bash
cd ~/
git clone https://github.com/Foundation-Devices/passport2.git
cd passport2
git checkout v2.1.2
```

### **Install Dependencies**

Several tools are required for building and verifying Passport’s firmware.

### Install Docker

:warning: Docker requires to add your user to the `docker` group which is root-equivalent and may pose a security risk for you. Consider using Podman if you don't want to add your user to the `docker` group. Building with `sudo` and Docker is not supported.

The installation of Docker is most easily achieved by installing Docker Desktop on your given platform using the official docs linked below. Follow those directions, launch Docker Desktop, and accept the terms before proceeding:

- [Windows](https://docs.docker.com/desktop/install/windows-install/)
- [MacOS](https://docs.docker.com/desktop/install/mac-install/)
- [Linux](https://docs.docker.com/desktop/install/linux-install/)
    - If you don’t want to require using `sudo` when running the `just` commands below, follow the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) to grant your user Docker permissions on Linux

### Install Podman (optional)

This step is optional if you already have Docker installed and your user is on the `docker` group.

Podman does not require root or adding your user to another group, so this option is recommended for non-developer users that want to verify the reproducibility of the firmware only.

- [Windows](https://podman.io/docs/installation#windows)
- [MacOS](https://podman.io/docs/installation#macos)
- [Linux](https://podman.io/docs/installation#installing-on-linux)

Also, the following configuration files might need to be created after installation:

- [Configuration files](https://podman.io/docs/installation#policyjson)

### Install Just

Just is a powerful tool that allows us to provide scripts to perform all the necessary steps of building and verification. In order to use Just, you will need to install it using the following instructions for your given operating system:

- [Installing Just](https://github.com/casey/just#installation)

You can also use the [following set of commands](https://github.com/casey/just#pre-built-binaries) to install Just to `~/bin` directly from Github on most operating systems:

```bash
# create ~/bin
mkdir -p ~/bin

# download and extract just to ~/bin/just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin

# add `~/bin` to the paths that your shell searches for executables
# this line should be added to your shells initialization file,
# e.g. `~/.bashrc` or `~/.zshrc`
export PATH="$PATH:$HOME/bin"

# just should now be executable
just --help
```

## **Building Passport Firmware**

### Build the reproducible builds Docker image

Now that we have all of the necessary dependencies, you can use `just` to run the correct commands to build the firmware necessary to verify Passport’s reproducibility.

First, let's be sure we are starting with a clean slate, as if you've built Passport's firmware in the past you may have some files and folders leftover that can cause issues.

```bash
just clean
```

Next, in order to build the firmware itself, we need to first build the Docker image that will include all the necessary dependencies and files for building the firmware in a reproducible way:

```bash
just build-docker
```

This command will take some time to run as it creates the image, including downloading and installing every tool necessary for the build process. As we use a Docker image here, not only will this ensure the binaries are always the same for a given version, but it also allows you to easily clean up after verifying the firmware and leave your system uncluttered.

If you want to opt to use Docker instead of Podman, then you can prepend set the `DOCKER_CMD` environment variable to `podman`, for example:

```bash
DOCKER_CMD=podman just build-docker
```

This applies to other commands shown here as well that would normally require Docker in order to run.

If you’d like to validate exactly how the `build-docker` Justfile command functions, you can find the relevant source code here:

- [passport2/Justfile#L8-L10](https://github.com/Foundation-Devices/passport2/blob/6c6249e2c15f52c59db56b12b5f84213806a6533/Justfile#L8-L10)
- [passport2/Dockerfile](https://github.com/Foundation-Devices/passport2/blob/main/Dockerfile)

### Build Passport’s firmware

Now that we have everything in place, we can actually build the firmware binaries for Passport with two simple commands:

```bash
just build-firmware color
```

If you instead want to reproduce firmware for Passport “Founder’s Edition,” use the following commands and substitute “MONO” for “COLOR” in filenames throughout the rest of this guide:

```bash
just build-firmware mono
```

These commands will take a few minutes as they build Passport’s firmware directly from the source code you downloaded earlier. Once they complete, you’ll have the completed binary available in `ports/stm32/build-Passport/`.

If you’d like to validate exactly how the `build-*` Justfile commands function, you can find the relevant source code here:

- [passport2/Justfile#L12-16](https://github.com/Foundation-Devices/passport2/blob/6c6249e2c15f52c59db56b12b5f84213806a6533/Justfile#L12-L16)
- [passport2/Justfile#L78-L86](https://github.com/Foundation-Devices/passport2/blob/6c6249e2c15f52c59db56b12b5f84213806a6533/Justfile#L78-L86)

## Verifying Passport Firmware

Now that we’ve built the binaries for Passport, we can verify the built binary and compare it to what we expect to see.

### Verify build hash

In order to verify that the binary produced matches what you should see, you can run the following command while passing the “Build hash” seen in the Github release notes published with the given version of Passport’s firmware. 

The syntax is `just verify-sha <build hash> color`, replacing `<build hash>` with the appropriate build hash (i.e. `0895...4520` for `v2.1.2`) and `color` with `mono` if reproducing firmware for Founder’s Edition devices:

```bash
$ just verify-sha 08959d69338eb33ab008ae6e74e111838cc60f39ef17befe401e77d1cc274520 color
Expected SHA:	08959d69338eb33ab008ae6e74e111838cc60f39ef17befe401e77d1cc274520
Actual SHA:	08959d69338eb33ab008ae6e74e111838cc60f39ef17befe401e77d1cc274520
Hashes match!
```

This means that the binary we’ve built matches what we at Foundation have also built and published as the expected hash. Next, we’ll be sure that this built binary ****also**** matches the release binary you’d install on Passport directly.

If your hashes do not match for any reason, stop immediately and contact us at [hello@foundation.xyz](mailto:hello@foundation.xyz)! We’ll help you investigate the cause of this discrepancy and get to the bottom of the issue.

If you’d like to validate exactly how the `verify-sha` command works and ensure it’s not lying to you about the hashes, you can see the source code here: 

- [passport2/Justfile](https://github.com/Foundation-Devices/passport2/blob/6c6249e2c15f52c59db56b12b5f84213806a6533/Justfile#L18-L34)

### Verify release binary hash

In order to compare the binary we just built with the one you install on Passport, you’ll need to strip out the signatures we use to ensure that Passport devices can only install legitimate firmware updates. As only we have the keys necessary to generate these signatures, there is no way for you to produce signed binaries with a matching hash. The way that we can still verify binaries, however, is to strip out the signatures from the header of the binary file and then compare your built binary to the release binary without signatures and ensure that they are the same, bit-for-bit.

First, download the corresponding firmware to your computer, i.e., `v2.1.2`, [directly from Github](https://github.com/Foundation-Devices/passport2/releases).

```bash
cd ~/passport2
wget https://github.com/Foundation-Devices/passport2/releases/download/v2.1.2/v2.1.2-passport.bin
```

Next, use the following command to strip Foundation’s signatures from the release binary:

```bash
dd if=v2.1.2-passport.bin of=v2.1.2-passport-no-header.bin ibs=2048 skip=1
```

This will create a version of the firmware file without the added signatures, allowing you to directly compare it to the binary you just built. Now we can compare the hashes of your built binary and the release binary using the following commands:

```bash
# Check the hash of the built binary one more time to easily compare
shasum -b -a 256 ports/stm32/build-Passport/firmware-COLOR.bin
08959d69338eb33ab008ae6e74e111838cc60f39ef17befe401e77d1cc274520 *ports/stm32/build-Passport/firmware-COLOR.bin

# Verify the hash of the release binary minus signatures
shasum -b -a 256 v2.1.2-passport-no-header.bin
08959d69338eb33ab008ae6e74e111838cc60f39ef17befe401e77d1cc274520 v2.1.2-passport-no-header.bin
```

If your hashes matched above, congratulations! You just successfully verified that the firmware you’re about to install on your Passport exactly matches the source code that is published on Github.

If your hashes do not match for any reason, stop immediately and contact us at [hello@foundation.xyz](mailto:hello@foundation.xyz)! We’ll help you investigate the cause of this discrepancy and get to the bottom of the issue.

### Verifying the firmware header (optional)

If you’d like to do further, optional, verification on the header you can perform the following command to dump and view the header being stripped away in hex:

```bash
xxd -l 2048 v2.1.2-passport.bin
```

For example, Passport `v2.1.2` contains the following header (abbreviated due to the majority of the header being zeroed out):

```
00000000: 5041 5353 7fce 7e64 4a75 6e20 3036 2c20  PASS..~dJun 06, 
00000010: 3230 3233 0000 322e 312e 3200 0000 4896  2023..2.1.2...H.
00000020: 1b00 ff00 0000 19db 1775 c78b a8b0 15f1  .........u......
00000030: cc09 cf97 2b7a b615 b1fa 4456 2bad b3d0  ....+z....DV+...
00000040: bb13 cb66 5801 3b4c 25b2 bf68 e0a3 4b64  ...fX.;L%..h..Kd
00000050: bcd5 1e2e 2a43 31ce 317b e8a7 ef5c 4488  ....*C1.1{...\D.
00000060: ee9e 24b9 0527 0000 0000 0000 0000 0000  ..$..'..........
00000070: 0000 0000 0000 0000 0000 0000 0000 0000  ................
...
000007f0: 0000 0000 0000 0000 0000 0000 0000 0000  ................
```

You can also verify the code that defines and creates the header structure in the following files in the source code:

- [passport2/ports/stm32/boards/Passport/include/fwheader.h](https://github.com/Foundation-Devices/passport2/blob/main/ports/stm32/boards/Passport/include/fwheader.h)
- [passport2/ports/stm32/boards/Passport/tools/cosign/cosign.c](https://github.com/Foundation-Devices/passport2/blob/main/ports/stm32/boards/Passport/tools/cosign/cosign.c)

## Installing your verified firmware

In order to install the firmware you just verified, you can follow our documentation below:

- [Installing the Firmware (Advanced Instructions)](https://docs.foundationdevices.com/firmware-update#installing-the-firmware-advanced-instructions)

Be sure to use the unmodified release binary you downloaded from Github above (i.e., `v2.1.2-passport.bin`) that still has our official signatures, as Passport will only allow you to install firmware that has been signed by at least two members of the Passport team.

You can also validate the firmware hashes on Passport before installing by viewing the file under Settings>Advanced>MicroSD>List Files and viewing the info for the binary, or after installing by holding down the "1" key while booting and scrolling to the right.

## Conclusion

We want to close out this guide by thanking our fantastic community, many of whom have tested out reproducibility or let us know when they run into any issues along the way. Open source and the verifiability and transparency it brings are core to our ethos at Foundation, and the ability to reproducibly build firmware for Passport is a core outpouring of that.

We can’t wait to see more of our community take this additional step and remove a little more trust from the process by verifying that each build is reproducible.
