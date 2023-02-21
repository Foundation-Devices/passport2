# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# ext_settings.py - Similar to settings, but in external flash and can have a secondary backup
#                   Two instances are used for external user settings in Gen 1.2, and flash cache
#                   in Gen 1 and Gen 1.2 (but at different memory locations)
#
# Notes:
# - Multiple slots are available which we rotate through randomly for flash wear leveling
# - All data is encrypted with an AES encryption key is derived from actual wallet secret
# - A 32-byte SHA is appended to the end of each slot as a checksum

import os
import ujson
import trezorcrypto
import ustruct
import gc
from uio import BytesIO
from sffile import SFFile
from utils import to_str, call_later_ms
from constants import SPI_FLASH_SECTOR_SIZE
from passport import mem


class ExtSettings:
    """Settings stored in external flash, with a secondary backup"""

    # The 'name' is for developer use only (e.g., debugging)
    def __init__(self, slots=None, slot_size=0, loop=None, name=None):
        self.slots = slots
        self.slot_size = slot_size
        self.loop = loop
        self.name = name
        self.max_json_len = self.slot_size - 32  # Checksum size

        self.is_dirty = 0
        self.my_pos = 0
        self.aes_key = b'\0' * 32
        self.current = self.default_values()
        self.overrides = {}     # volatile overide values
        self.last_save_slots = [-1, -1]

        # NOTE: We don't load the settings initially since we don't have the AES key until
        #       the user logs in successfully.
        # self.load()

    def get_aes(self, pos):
        # Build AES key for en/decrypt of specific block.
        # Include the slot number as part of the initial counter (CTR)
        return trezorcrypto.aes(trezorcrypto.aes.CTR, self.aes_key, ustruct.pack('<4I', 4, 3, 2, pos))

    def set_key(self, new_secret=None):
        from common import pa
        from stash import blank_object

        key = None
        mine = False

        if not new_secret:
            if pa.is_successful() or pa.is_secret_blank():
                # read secret and use it.
                new_secret = pa.fetch()
                mine = True

        if new_secret:
            # print('====> new_secret={}'.format(new_secret))
            # hash up the secret... without decoding it or similar
            assert len(new_secret) >= 32

            s = trezorcrypto.sha256(new_secret)

            for round in range(5):
                s.update('pad')

                s = trezorcrypto.sha256(s.digest())

            key = s.digest()

            if mine:
                blank_object(new_secret)

            # for restore from backup case, or when changing (created) the seed
            self.aes_key = key
            # print('====> aes_key={}'.format(self.aes_key))

    def load(self):
        # Search all slots for any we can read, decrypt that,
        # and pick the newest one (in unlikely case of dups)
        from common import sf

        # reset
        self.current.clear()
        self.overrides.clear()
        self.my_pos = 0
        self.is_dirty = 0

        # 4k, but last 32 bytes are a SHA (itself encrypted)

        buf = bytearray(4)
        empty = 0
        for pos in self.slots:
            # print('pos={}'.format(pos))
            gc.collect()

            sf.read(pos, buf)
            if buf[0] == buf[1] == buf[2] == buf[3] == 0xff:
                # print('probably an empty page')
                # erased (probably)
                empty += 1
                continue

            # check if first 2 bytes makes sense for JSON
            aes = self.get_aes(pos)
            chk = aes.decrypt(b'{"')

            if chk != buf[0:2]:
                # print('Doesn\'t look like JSON')
                # doesn't look like JSON meant for me
                continue

            # probably good, read it
            aes = self.get_aes(pos)

            chk = trezorcrypto.sha256()
            expect = None

            with SFFile(pos, length=self.slot_size, pre_erased=True) as fd:
                for i in range(self.slot_size / 32):
                    enc = fd.read(32)
                    b = aes.decrypt(enc)

                    # print('i={}: {}'.format(i, bytes_to_hex_str(b)))
                    if i != (self.slot_size / 32 - 1):
                        mem.ext_settings_buf[i * 32:(i * 32) + 32] = b
                        chk.update(b)
                    else:
                        expect = b

            try:

                # verify checksum in last 32 bytes
                actual = chk.digest()
                # print('  Expected: {}'.format(expect))
                # print('  Actual:   {}'.format(actual))
                if expect != actual:
                    # print('ERROR: Checksum doesn\'t match!')
                    # TODO: Probably want to erase this sector
                    continue

                # loads() can't work from a byte array, and converting to
                # bytes here would copy it; better to use file emulation.
                fd = BytesIO(mem.ext_settings_buf)
                d = ujson.load(fd)
            except BaseException:
                # One in 65k or so chance to come here w/ garbage decoded, so
                # not an error.
                continue

            _revision = d.get('_revision', 0)
            # print('Candidate _revision={}'.format(_revision))
            # print('Last candidate _revision={}'.format(self.current.get('_revision', -1)))
            if _revision > self.current.get('_revision', -1):
                # print('Possible winner: _revision={}'.format(_revision))
                # print('data={}'.format(d))
                # likely winner
                self.current = d
                self.my_pos = pos
                # print("ext_settings: data @ %d w/ _revision=%d" % (pos, _revision))
            # else:
            #     print('Cleaning up stale data')
            #     # stale data seen; clean it up.
            #     assert self.current['_revision'] > 0
            #     # print("ext_settings: cleanup @ %d" % pos)
            #     self.erase_cache_entry(pos)

        # Do some memory cleanup after loading to prevent fragmentation
        gc.collect()

        # done, if we found something
        if self.my_pos:
            # print('{}: ExtSettings Load successful!: current={}'.format(to_str(self.current), self.name))
            return

        # print('{}: Nothing found...fall back to defaults'.format(self.name))
        # nothing found.
        self.my_pos = 0
        self.current = self.default_values()
        self.overrides.clear()

        if empty == len(self.slots):
            # Whole thing is blank. Bad for plausible deniability. Write 3 slots
            # with garbage. They will be wasted space until it fills.
            blks = list(self.slots)
            trezorcrypto.random.shuffle(blks)

            h = trezorcrypto.random.bytes(256)
            for pos in blks[0:3]:
                for i in range(0, self.slot_size, 256):
                    sf.wait_done()
                    sf.write(pos + i, h)

    def get(self, kn, default=None):
        if kn in self.overrides:
            return self.overrides.get(kn)
        else:
            # Special case for xfp and xpub -- make sure they exist and create if not
            if kn not in self.current:
                if kn == 'xfp' or kn == 'xpub' or kn == 'root_xfp':
                    try:
                        # Update xpub/xfp in settings after creating new wallet
                        import stash
                        from common import system

                        # system.show_busy_bar()
                        with stash.SensitiveValues() as sv:
                            sv.capture_xpub()
                    except Exception as e:
                        # print('ERROR: Cannot create xfp/xpub: e={}'.format(e))
                        # We tried to create it, but if creation fails, just let the caller handle the error
                        pass
                    finally:
                        # system.hide_busy_bar()
                        # These are overrides, so return them from there
                        return self.overrides.get(kn)

            return self.current.get(kn, default)

    def changed(self):
        self.is_dirty += 1
        if self.is_dirty < 2 and self.loop:
            call_later_ms(250, self.write_out())

    def set(self, kn, v):
        # print('set({}, {}'.format(kn, v))
        self.current[kn] = v
        self.changed()

    def set_volatile(self, kn, v):
        self.overrides[kn] = v

    def clear_volatile(self, kn):
        if kn in self.overrides:
            del self.overrides[kn]

    def remove(self, kn):
        # print('remove(\'{}\') called!'.format(kn))
        if kn in self.current:
            self.current.pop(kn, None)
            self.changed()

    def remove_regex(self, pattern):
        import re
        pattern = re.compile(pattern)
        matches = [k for k in self.current if pattern.search(k)]
        for k in matches:
            self.remove(k)

    def clear(self):
        # print('clear() called!')
        # could be just:
        #       self.current = {}
        # but accomodating the simulator here
        rk = [k for k in self.current if k[0] != '_']
        for k in rk:
            del self.current[k]

        self.changed()

    def reset(self):
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        # print(' RESET SETTINGS FLASH')
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

        rev = self.current['_revision']
        self.current = self.default_values()
        self.overrides.clear()

        self.current['_revision'] = rev + 1
        self.changed()

    async def write_out(self):
        # delayed write handler
        if not self.is_dirty:
            # someone beat me to it
            return

        # Was sometimes running low on memory in this area: recover
        try:
            gc.collect()
            self.save()
        except MemoryError:
            call_later_ms(250, self.write_out())

    def find_spot(self, not_here=0):
        # search for a blank sector to use
        # - check randomly and pick first blank one (wear leveling, deniability)
        # - we will write and then erase old slot
        # - if "full", blow away a random one
        from common import sf

        # print('find_spot(): last_save_slots={}'.format(self.last_save_slots))
        options = [s for s in self.slots if s != not_here and s not in self.last_save_slots]
        trezorcrypto.random.shuffle(options)

        buf = bytearray(16)
        for pos in options:
            sf.read(pos, buf)
            if set(buf) == {0xff}:
                # blank
                return sf, pos

        victim = options[0]

        # Nowhere to write! (probably a bug because we have lots of slots)
        # ... so pick a random slot and kill what it had
        # print('ERROR: self.slots full? Picking random slot to blow away...victim={}'.format(victim))

        self.erase_cache_entry(victim)

        return sf, victim

    def erase_cache_entry(self, start_pos):
        from common import sf
        # print('erase_cache_entry(): pos={}'.format(start_pos))
        sf.wait_done()
        for i in range(self.slot_size // SPI_FLASH_SECTOR_SIZE):
            addr = start_pos + (i * SPI_FLASH_SECTOR_SIZE)
            # print('{}: erasing addr={}'.format(self.name, addr))
            sf.sector_erase(addr)
            sf.wait_done()

    def erase_all(self):
        for pos in self.slots:
            self.erase_cache_entry(pos)
        self.blank()

    def save(self):
        # Make two saves in case one is corrupted
        self.do_save(erase_old_pos=True)
        self.do_save(erase_old_pos=False)

    def do_save(self, erase_old_pos=True):
        # print('do_save({})'.format(erase_old_pos))
        # render as JSON, encrypt and write it.
        self.current['_revision'] = self.current.get('_revision', 1) + 1

        _, pos = self.find_spot(self.my_pos)
        self.save_impl(pos, erase_old_pos=erase_old_pos)

        # print('save(): sf={}, pos={}'.format(sf, pos))

    def save_impl(self, pos, erase_old_pos=True):
        aes = self.get_aes(pos)

        with SFFile(pos, pre_erased=True, max_size=self.slot_size) as fd:
            chk = trezorcrypto.sha256()

            # first the json data
            d = ujson.dumps(self.current)
            # print('pos: {}'.format(pos))
            # print('current: {}'.format(self.current))
            # print('data: {}'.format(bytes_to_hex_str(d)))

            # pad w/ zeros
            data_len = len(d)
            pad_len = self.max_json_len - data_len
            if pad_len < 0:
                # print('ERROR: JSON data is too big!')
                return

            fd.write(aes.encrypt(d))
            chk.update(d)
            del d

            # print('data_len={} pad_len={}'.format(data_len, pad_len))

            while pad_len > 0:
                here = min(32, pad_len)

                pad = bytes(here)
                fd.write(aes.encrypt(pad))
                chk.update(pad)
                # print('pad: {}'.format(bytes_to_hex_str(pad)))

                pad_len -= here

            # print('fd.tell()={}'.format(fd.tell()))

            digest = chk.digest()
            # print('Saving with digest={}'.format(digest))
            enc_digest = aes.encrypt(digest)
            # print('Encrypted digest={}'.format(enc_digest))
            fd.write(enc_digest)
            # print('fd.tell()={}  self.slot_size={}'.format(fd.tell(), self.slot_size))
            assert fd.tell() == self.slot_size

        # erase old copy of data for additional privacy
        if erase_old_pos and self.my_pos and self.my_pos != pos:
            self.erase_cache_entry(self.my_pos)

        self.my_pos = pos
        self.last_save_slots = [self.last_save_slots[-1], self.my_pos]
        self.is_dirty = 0

    def merge(self, prev):
        # take a dict of previous values and merge them into what we have
        self.current.update(prev)

    def blank(self):
        # erase current copy of values in flash cache; older ones may exist still
        # - use when clearing the seed value

        if self.my_pos:
            self.erase_cache_entry(self.my_pos)
            self.my_pos = 0

        # act blank too, just in case.
        self.current.clear()
        self.is_dirty = 0

    @staticmethod
    def default_values():
        # Please try to avoid defaults here... It's better to put into code
        # where value is used, and treat undefined as the default state.
        return dict(_revision=0, _schema=1)

# EOF
