# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# sflash.py - SPI Flash
#
# Layout for project:
#   - 917K PSBT incoming (MAX_TXN_LEN)
#   - 917K PSBT outgoing (MAX_TXN_LEN)
#   - The previous two regions are only used when signing PSBTs.
#   - The same space is also used to hold firmware updates.
#   - 256k flash cache - similar to settings, but for UTXOs and wallet address cache
#

from micropython import const

# NOTE: commands starting with an underscore are not meant to be used from
# outside this module. (const() prevents it, only on micropython)
CMD_READ = const(0x03)
CMD_FAST_READ = const(0x0b)
_CMD_WRSR = const(0x01)
_CMD_WRITE = const(0x02)
_CMD_RDSR = const(0x05)
_CMD_WREN = const(0x06)
_CMD_RDCR = const(0x35)
_CMD_RD_DEVID = const(0x9f)
_CMD_SEC_ERASE = const(0x20)
_CMD_BLK_ERASE = const(0xd8)
_CMD_C4READ = const(0xeb)


NUM_BUFS_TO_COMPARE = 3
MAX_SPI_REPEATED_READ_LEN = 1024
MAX_READ_ATTEMPTS = 9


class SPIFlash:
    """SPI flash driver

    This differs from the existing Micro-Python driver on `../external/micropython/drivers/memory/spiflash.c`
    because:

    - It's not exposed as a Python object.
    - Wastes 4K on a buffer.
    """

    # must write with this page size granularity
    PAGE_SIZE = 256
    # must erase with one of these size granulatrty!
    SECTOR_SIZE = 4096
    BLOCK_SIZE = 65536

    def __init__(self, spi, cs):
        """Initialize the SPI flash driver

        - `spi` is the SPI bus object where the flash is connected to.
        - `cs` corresponds to the CS pin of the flash. It's a GPIO pin.

        The SPI bus is not initialized here in order to aid testing and avoid
        depending on the hardware in order to test, so that the `spi` and `cs`
        parameters can be mocked.
        """

        self.spi = spi
        self.cs = cs

    @staticmethod
    def default():
        """Creates a SPI flash driver object based on the default configuration of the hardware"""

        from machine import Pin, SPI
        spi = SPI(4, baudrate=8000000)
        cs = Pin('SF_CS', Pin.OUT)
        return SPIFlash(spi, cs)

    def _cmd(self, _cmd, addr=None, complete=True, pad=False):
        """Send a command to the device"""

        if addr is not None:
            buf = bytes([_cmd, (addr >> 16) & 0xff, (addr >> 8) & 0xff, addr & 0xff])
        else:
            buf = bytes([_cmd])

        if pad:
            buf = buf + b'\0'

        self.cs.low()
        self.spi.write(buf)
        if complete:
            self.cs.high()

    def _read_reg(self, _cmd, length):
        """Read a register from the device"""

        rv = bytearray(length)
        self._cmd(_cmd, complete=False)
        self.spi.readinto(rv)
        self.cs.high()
        return rv

    def read_impl(self, address, buf, cmd=CMD_FAST_READ):
        """Random read (fast mode, because why wouldn't we?!)

        - `cmd` MUST be either `CMD_FAST_READ` or `CMD_READ`
        """

        assert cmd == CMD_FAST_READ or cmd == CMD_READ
        self._cmd(cmd, address, complete=False, pad=True)
        self.spi.readinto(buf)
        self.cs.high()

    def read(self, address, buf, cmd=CMD_FAST_READ):
        if len(buf) > MAX_SPI_REPEATED_READ_LEN:
            print('Large spi_read() len={}'.format(len(buf)))
            return self.read_impl(address, buf, cmd)

        # Make bufs for the copies of the data
        temp_bufs = []
        for i in range(NUM_BUFS_TO_COMPARE):
            temp_bufs.append(bytearray(len(buf)))

        num_reads = 0
        curr_idx = 0

        while True:
            retry = False
            self.read_impl(address, temp_bufs[curr_idx])

            # Next index, plus wrap around
            curr_idx = (curr_idx + 1) % NUM_BUFS_TO_COMPARE
            num_reads += 1

            # Compare the buffers, but only after we've read the minimum number of times
            if num_reads >= NUM_BUFS_TO_COMPARE:
                for i in range(NUM_BUFS_TO_COMPARE - 1):
                    if temp_bufs[i] != temp_bufs[i + 1]:
                        print(
                            'SPIFlash().read(): Buffers are not equal!  address={}, len={}, num_reads={}'.format(
                                address, len, num_reads))
                        retry = True
                        break

            if (num_reads < NUM_BUFS_TO_COMPARE) or (retry and num_reads < MAX_READ_ATTEMPTS):
                continue
            else:
                # Copy the buffer out to the caller.
                # Either we know they are all equal, so it doesn't matter which one we
                # pick, or we don't know which is the right one, so just return the first one.
                # TODO: Could add more code in the case of MAX_READ_ATTEMPTS, to see which
                #       buffer has the majority, but that COULD still be all FFs in the majority,
                #       but the chances of that are lower.
                buf[:] = temp_bufs[0]
                return

    def write(self, address, buf):
        """Page program

        The page must be already erased

        - `buf` length MUST NOT be higher than 256 bytes and MUST NOT exceed
        the page boundary.
        """

        assert 1 <= len(buf) <= 256  # "max 256"
        assert address & ~0xff == (address + len(buf) - 1) & ~0xff  # "page boundary"
        self._cmd(_CMD_WREN)
        self._cmd(_CMD_WRITE, address, complete=False)
        self.spi.write(buf)
        self.cs.high()

    def is_busy(self):
        """Returns the status of the Write In Progress bit (WIP)"""

        r = self._read_reg(_CMD_RDSR, 1)
        return bool(r[0] & 0x01)

    def wait_done(self):
        """Wait until the WIP bit is not set"""

        # TODO: could this be fancier?
        while True:
            if not self.is_busy():
                return

    def sector_erase(self, address):
        """Erase a sector

        The operation takes around 40 to 200 ms to complete, the `is_busy()`
        method can be polled to check for completon.

        - `address` needs to be aligned to the `SPIFlash.SECTOR_SIZE` value.
        """

        assert address % self.SECTOR_SIZE == 0      # "not sector start"
        self._cmd(_CMD_WREN)
        self._cmd(_CMD_SEC_ERASE, address)

    def block_erase(self, address):
        """Erase a block

        - `address` needs to be aligned to the `SPIFlash.BLOCK_SIZE` value.
        """

        assert address % self.BLOCK_SIZE == 0     # "not block start"
        self._cmd(_CMD_WREN)
        self._cmd(_CMD_BLK_ERASE, address)

# EOF
