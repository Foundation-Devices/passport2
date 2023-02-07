# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-only

from utils import file_exists

_SIZE = 1024 * 1024 * 8
SPI_FLASH_SIM_PATH = 'spi_flash.bin'


class SPIFlash:
    PAGE_SIZE = 256
    SECTOR_SIZE = 4096
    BLOCK_SIZE = 65536

    array = bytearray(_SIZE)

    def __init__(self):
        self.load()

    @staticmethod
    def default():
        return SPIFlash()

    def read(self, address, buf, **kw):
        # random read
        buf[0:len(buf)] = self.array[address:address + len(buf)]

    def write(self, address, buf):
        # 'page program', must already be erased
        assert 1 <= len(buf) <= 256, "max 256"
        assert address & ~0xff == (address + len(buf) - 1) & ~0xff, \
            "page aligned only: addr=0x%x len=0x%x" % (address, len(buf))

        #self.array[address:address+len(buf)] = buf
        # emulate flash memory: can only go from 1=>0
        for i in range(len(buf)):
            self.array[address + i] &= buf[i]

        self.save()

    def is_busy(self):
        # always instant
        return False

    def wait_done(self):
        return

    def chip_erase(self):
        for i in range(_SIZE):
            self.array[i] = 0xff

    def sector_erase(self, address):
        for i in range(self.SECTOR_SIZE):
            self.array[address + i] = 0xff

    def block_erase(self, address):
        # erase 64k at once
        assert address % 65536 == 0, "not block start"
        for i in range(self.BLOCK_SIZE):
            self.array[address + i] = 0xff

    def save(self):
        with open(SPI_FLASH_SIM_PATH, 'w') as f:
            f.write(self.array)

    def load(self):
        if file_exists(SPI_FLASH_SIM_PATH):
            with open(SPI_FLASH_SIM_PATH, 'rb') as f:
                self.array = bytearray(f.read())
                # print('SPIFlash.load(): len(self.array)={}'.format(len(self.array)))
        else:
            self.array = bytearray(_SIZE)
            self.save()

# EOF
