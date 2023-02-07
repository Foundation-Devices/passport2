<!--
SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>

SPDX-License-Identifier: GPL-3.0-only

SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Passport Desktop Simulator

## Usage

`just sim`

## Requirements

- Uses `xterm` for console input and output.
- This directory has additional `requirements.txt` (a superset of other requirements of the project)
- Run `brew install sdl2` before/after doing python requirements
- Run `just sim`

# MacOS building

- Follow instructions on <https://github.com/micropython/micropython>
- probably: `brew install libffi` if not already present
- to get `pkg-config libffi` to output useful things, need this:

```
setenv PKG_CONFIG_PATH /usr/local/opt/libffi/lib/pkgconfig
```

- But that's in the Makefile now

# Other OS

- Sorry we haven't gotten around to that yet, but certainly would be possible to build
  this on Linux or FreeBSD... but not Windows.


