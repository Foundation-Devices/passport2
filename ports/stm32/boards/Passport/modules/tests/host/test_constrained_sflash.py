# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
from pathlib import Path


PROJECT_ROOT_PARENT_INDEX = 7
ROOT = Path(__file__).resolve().parents[PROJECT_ROOT_PARENT_INDEX]


def test_sparse_flash_partial_and_repeated_programming(tmp_path, monkeypatch):
    path = ROOT / 'simulator/sim_modules/constrained_sflash.py'
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, '_BACKING_FILE', str(tmp_path / 'flash.bin'))
    flash = module.SPIFlash()
    try:
        flash.write(17, b'\xf0\x55')
        page = bytearray(256)
        flash.read(0, page)
        assert page == b'\xff' * 17 + b'\xf0\x55' + b'\xff' * 237
        flash.write(17, b'\x0f\xff')
        flash.read(0, page)
        assert page[17:19] == b'\x00\x55'
        flash.sector_erase(0)
        flash.write(20, b'\xaa')
        flash.read(0, page)
        assert page == b'\xff' * 20 + b'\xaa' + b'\xff' * 235
    finally:
        flash._file.close()
