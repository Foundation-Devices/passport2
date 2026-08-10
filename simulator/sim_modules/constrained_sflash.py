# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Low-heap SPI flash model for constrained simulator startup tests.

The regular simulator keeps the complete 8 MiB flash in a Python bytearray.
That is convenient for interactive use, but it makes the simulator unable to
exercise Passport's real 276 KiB MicroPython heap. This model stores written
pages in a sparse host file and keeps only a one-bit-per-page allocation map in
the garbage-collected heap.
"""

_SIZE = 8 * 1024 * 1024
_PAGE_SIZE = 256
_PAGE_COUNT = _SIZE // _PAGE_SIZE
_BACKING_FILE = 'spi_flash_sparse.bin'


class SPIFlash:
    PAGE_SIZE = _PAGE_SIZE
    SECTOR_SIZE = 4096
    BLOCK_SIZE = 65536

    _written_pages = bytearray(_PAGE_COUNT // 8)
    _file = None

    def __init__(self):
        if SPIFlash._file is None:
            SPIFlash._file = open(_BACKING_FILE, 'w+b')

    @staticmethod
    def default():
        return SPIFlash()

    @classmethod
    def _is_written(cls, page):
        return cls._written_pages[page >> 3] & (1 << (page & 7))

    @classmethod
    def _mark_written(cls, page):
        cls._written_pages[page >> 3] |= 1 << (page & 7)

    @classmethod
    def _mark_erased(cls, page):
        cls._written_pages[page >> 3] &= ~(1 << (page & 7))

    def read(self, address, buf, **kw):
        assert 0 <= address <= _SIZE - len(buf)
        offset = 0
        while offset < len(buf):
            absolute = address + offset
            page = absolute // self.PAGE_SIZE
            in_page = absolute % self.PAGE_SIZE
            count = min(len(buf) - offset, self.PAGE_SIZE - in_page)
            if self._is_written(page):
                self._file.seek(absolute)
                buf[offset:offset + count] = self._file.read(count)
            else:
                for i in range(offset, offset + count):
                    buf[i] = 0xff
            offset += count

    def write(self, address, buf):
        assert 1 <= len(buf) <= self.PAGE_SIZE
        assert 0 <= address <= _SIZE - len(buf)
        assert address // self.PAGE_SIZE == (address + len(buf) - 1) // self.PAGE_SIZE
        self._file.seek(address)
        self._file.write(buf)
        self._mark_written(address // self.PAGE_SIZE)

    def is_busy(self):
        return False

    def wait_done(self):
        return

    def chip_erase(self):
        for i in range(len(self._written_pages)):
            self._written_pages[i] = 0

    def _erase_pages(self, address, size):
        assert address % size == 0
        first = address // self.PAGE_SIZE
        count = size // self.PAGE_SIZE
        for page in range(first, first + count):
            self._mark_erased(page)

    def sector_erase(self, address):
        self._erase_pages(address, self.SECTOR_SIZE)

    def block_erase(self, address):
        self._erase_pages(address, self.BLOCK_SIZE)
