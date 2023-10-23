#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

USER_UID=$(id -u)
USER_GID=$(id -g)

# These can be overriden, for example:
#
# DOCKER='sudo docker' ./run.sh ...
#
# In order to build on systems where the user is not on the docker
# group.
DOCKER="${DOCKER:-docker}"
IN_DOCKER="${IN_DOCKER:-false}"
USE_DOCKER="${USE_DOCKER:-true}"
DOCKER_IMAGE="${DOCKER_IMAGE:-foundation-devices/passport2:latest}"
CONTAINER_UID=${CONTAINER_UID:-$USER_UID}
CONTAINER_GID=${CONTAINER_GID:-$USER_GID}

# Retrieve the directory where the script is located.
#
# From:
# https://stackoverflow.com/questions/59895/how-do-i-get-the-directory-where-a-bash-script-is-located-from-within-the-script
SOURCE=${BASH_SOURCE[0]}
while [ -L "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "$SOURCE")
  [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )

if [ "$IN_DOCKER" = true ] || [ "$USE_DOCKER" = false ];
then
    $@
else
    ${DOCKER} run --rm \
                  --volume $DIR:/workspace \
                  --user ${CONTAINER_UID}:${CONTAINER_GID} \
                  ${DOCKER_IMAGE} \
                  "$*"
fi
