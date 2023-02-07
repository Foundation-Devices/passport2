# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test that the SPIFlash class works.

import sys
import os
import pytest

sys.path.insert(1, os.path.join(sys.path[0], '..'))


class FakePin:
    def __init__(self) -> None:
        self.level = True

    def low(self):
        self.level = False

    def high(self):
        self.level = True


class FakeSPIFlash:
    # 64 MBit memory - 8 KiB
    _MEMORY_SIZE = 8 * 1024 * 1024

    def __init__(self) -> None:
        self.cs = FakePin()
        self.write_enable = False
        self.write_in_progress = False
        self.addr = None
        self.op = None
        self.memory = bytearray(self._MEMORY_SIZE)

    def write(self, buf):
        from sflash import _CMD_WREN, _CMD_CHIP_ERASE, _CMD_WRITE, _CMD_RDSR, CMD_READ, CMD_FAST_READ

        assert self.cs.level is False
        assert len(buf) >= 1

        if self.op == _CMD_WRITE:
            assert self.write_enable

            start = self.addr
            end = self.addr + len(buf)

            self.memory[start:end] = buf

            self.op = None
            self.write_in_progress = True
            return

        self.op = None
        self.addr = None

        op = buf[0]
        if op == _CMD_WREN:
            assert len(buf) == 1
            self.write_enable = True
        elif op == _CMD_CHIP_ERASE:
            assert len(buf) == 1
            self.write_in_progress = True
            self.memory = bytearray(self._MEMORY_SIZE)
        elif op == _CMD_WRITE:
            # 1 byte for op, 2 bytes for address, 1 byte at least to write
            assert len(buf) >= 4
            assert self.write_enable
            assert self.write_in_progress is False

            self.op = _CMD_WRITE

            addr = buf[1] << 16 | buf[2] << 8 | buf[3]
            data = buf[4:len(buf)]
            start = addr
            end = addr + len(data)

            self.memory[start:end] = data[:]
            self.addr = end
        elif op == _CMD_RDSR:
            assert len(buf) == 1
            self.op = _CMD_RDSR
        elif op == CMD_READ or op == CMD_FAST_READ:
            assert len(buf) == 5
            self.op = op
            self.addr = buf[1] << 16 | buf[2] << 8 | buf[3]

    def readinto(self, buf):
        from sflash import CMD_READ, _CMD_RDSR, CMD_FAST_READ

        assert self.cs.level is False
        assert self.op is not None
        assert len(buf) >= 1

        if self.op == _CMD_RDSR:
            assert len(buf) == 1
            # Make sure the WIP bit is set at least for one read of the
            # SDSR register.
            if self.write_in_progress:
                buf[0] = 0x01
                self.write_in_progress = False
            else:
                buf[0] = 0x00
        elif self.op == CMD_FAST_READ or self.op == CMD_READ:
            assert len(buf) >= 1
            assert self.write_in_progress is False
            assert self.addr is not None

            start = self.addr
            end = self.addr + len(buf)
            buf[0:len(buf)] = self.memory[start:end]

        self.op = None


@pytest.fixture
def fake_spi_flash():
    return FakeSPIFlash()


@pytest.fixture
def spi_flash(fake_spi_flash):
    from sflash import SPIFlash

    return SPIFlash(fake_spi_flash, fake_spi_flash.cs)


def test_wait(spi_flash):
    spi_flash.wait_done()
    assert spi_flash.cs.level is True


def test_chip_erase(spi_flash):
    marker = b'test sequence'
    spi_flash.spi.memory[0:len(marker)] = b'test sequence'

    # Erase and wait for completion
    spi_flash.chip_erase()
    assert spi_flash.cs.level is True

    spi_flash.wait_done()
    assert spi_flash.cs.level is True

    assert spi_flash.spi.memory[0:len(marker)] != marker


def test_write(spi_flash):
    marker = b'test_array'
    spi_flash.write(0x00001000, marker)
    assert spi_flash.cs.level is True

    spi_flash.wait_done()
    assert spi_flash.cs.level is True
    assert spi_flash.spi.memory[0x00001000:0x00001000 + len(marker)] == bytearray(marker)


def test_read(spi_flash):
    marker = b'test sequence'
    spi_flash.spi.memory[0:len(marker)] = b'test sequence'

    buf = bytearray(len(marker))
    spi_flash.read(0x00000000, buf)


def test_read_write_roundtrip(spi_flash):
    marker = b'test_array'
    spi_flash.write(0x00001000, marker)
    assert spi_flash.cs.level is True

    spi_flash.wait_done()
    assert spi_flash.cs.level is True

    buf = bytearray(len(marker))
    spi_flash.read(0x00001000, buf)
    assert spi_flash.cs.level is True

    assert marker == buf
