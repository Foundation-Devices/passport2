# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# settings.py - manage a few key values that aren't super secrets
#
# Goals:
# - Single wallet settings
# - Wear leveling of the flash
# - If no settings are readable, erase flash and start over
#
# Result:
# - up to 4k of values supported (after json encoding)
# - encrypted and stored in SPI flash, in last 128k area
# - AES encryption key is derived from actual wallet secret
# - if logged out, then use fixed key instead (ie. it's public)
# - to support multiple wallets and plausible deniablity, we
#   will preserve any noise already there, and only replace our own stuff
# - you cannot move data between slots because AES-CTR with CTR seed based on slot #
# - SHA check on decrypted data
#
import ujson
import ustruct
import uctypes
import gc
import trezorcrypto
from uio import BytesIO
from utils import call_later_ms

# Base address for internal memory-mapped flash used for settings: 0x81E0000
SETTINGS_FLASH_START = const(0x81E0000)
SETTINGS_FLASH_LENGTH = const(0x20000)  # 128K
SETTINGS_FLASH_END = SETTINGS_FLASH_START + SETTINGS_FLASH_LENGTH - 1
DATA_SIZE = const(8192 - 32)
BLOCK_SIZE = const(8192)

# Setting values:
#   xfp = master xpub's fingerprint (32 bit unsigned)
#   xpub = master xpub in base58
#   chain = 3-letter codename for chain we are working on (BTC)
#   words = (bool) BIP39 seed words exist (else XPRV or master secret based)
#   shutdown_timeout = idle timeout period (seconds)
#   _revision = internal version number for data - incremented every time the data is saved
#   terms_ok = customer has signed-off on the terms of sale
#   multisig = list of defined multisig wallets (complex)
#   multisig_policy = trust/import/distrust xpubs found in PSBT files
#   accounts = array of accounts configured on this device
#   screen_brightness = 0 to 100, 999 for automatic
#   enable_passphrase = True to show Set Passphrase item in main menu, False to hide it
#   backup_quiz = True if backup password quiz was passed; False if not

# These are the data slots available to use. We have 32 slots
# for flash wear leveling.
SLOT_ADDRS = range(SETTINGS_FLASH_START, SETTINGS_FLASH_END, BLOCK_SIZE)


class Settings:

    def __init__(self, loop=None, serial=None):
        from passport import SettingsFlash
        from common import system  # This is defined before Settings is created, so OK to use here

        self.loop = loop
        self.is_dirty = 0

        # AES key is based on the serial number now instead of the PIN
        # We don't store anything critical in the settings, so this level of protection is fine,
        # and avoids having 2 sets of settings (one with a zero AES key and one with the PIN-based key).
        serial = system.get_serial_number()
        # print('Settings: serial={}'.format(serial))
        self.aes_key = trezorcrypto.sha256(serial).digest()
        # print('Settings: aes_key={}'.format(self.aes_key))

        self.curr_dict = self.default_values()
        self.overrides = {}     # volatile overide values

        self.flash = SettingsFlash()

        self.load()

    def get_aes(self, flash_offset):
        # Build AES key for en/decrypt of specific block.
        # Include the slot number as part of the initial counter (CTR)
        return trezorcrypto.aes(trezorcrypto.aes.CTR, self.aes_key, ustruct.pack('<4I', 4, 3, 2, flash_offset))

    def load(self):
        # Search all slots for any we can read, decrypt them and pick the newest one
        from common import system

        system.turbo(True)
        try:
            # reset
            self.curr_dict.clear()
            self.overrides.clear()
            self.addr = 0
            self.is_dirty = 0

            for addr in SLOT_ADDRS:
                # print('Trying to load at {}'.format(hex(addr)))
                buf = uctypes.bytearray_at(addr, 4)
                if buf[0] == buf[1] == buf[2] == buf[3] == 0xff:
                    # print('  Slot is ERASED')
                    # erased (probably)
                    continue

                # check if first 2 bytes makes sense for JSON
                flash_offset = (addr - SETTINGS_FLASH_START) // BLOCK_SIZE
                aes = self.get_aes(flash_offset)
                chk = aes.decrypt(b'{"')

                if chk != buf[0:2]:
                    # doesn't look like JSON, so skip it
                    # print('  Slot does not contain JSON')
                    continue

                # probably good, so prepare to read it
                aes = self.get_aes(flash_offset)
                chk = trezorcrypto.sha256()
                expect = None

                # Our flash is memory mapped, so we read directly by address
                buf = uctypes.bytearray_at(addr, DATA_SIZE)

                # Get a bytearray for the SHA256 at the end
                expected_sha = uctypes.bytearray_at(addr + DATA_SIZE, 32)

                # Decrypt and check hash
                b = aes.decrypt(buf)

                # Add the decrypted result to the SHA
                chk.update(b)

                try:
                    # verify hash in last 32 bytes
                    assert expected_sha == chk.digest()

                    # FOUNDATION
                    # loads() can't work from a byte array, and converting to
                    # bytes here would copy it; better to use file emulation.
                    # print('json = {}'.format(b))
                    d = ujson.load(BytesIO(b))
                except BaseException:
                    # One in 65k or so chance to come here w/ garbage decoded, so
                    # not an error.
                    # print('ERROR? Unable to decode JSON')
                    continue

                curr_revision = d.get('_revision', 0)
                if curr_revision > self.curr_dict.get('_revision', -1):
                    # print('Found candidate JSON: {}'.format(d))
                    # A newer entry was found
                    self.curr_dict = d
                    self.addr = addr

            # If we loaded settings, then we're done
            if self.addr:
                # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
                # print('LOADED SETTINGS! _revision={} addr={}'.format(self.curr_dict.get('_revision'), hex(addr)))
                # print('values: {}'.format(to_str(self.curr_dict)))
                # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

                system.turbo(False)
                return

            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            # print(' UNABLE TO LOAD SETTINGS: key={}'.format(self.aes_key))
            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

            # If no entries were found, which means this is either the first boot or we have corrupt settings, so raise
            # an exception so we erase and set default
            # raise ValueError('Flash is either blank or corrupt, so me must reset to recover to avoid a crash!')
            self.curr_dict = self.default_values()
            self.overrides.clear()
            self.addr = 0

        except Exception as e:
            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            # print('Exception in settings.load(): e={}'.format(e))
            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            self.reset()
            self.is_dirty = True
            self.write_out()

        system.turbo(False)

    def get(self, kn, default=None):
        if kn in self.overrides:
            return self.overrides.get(kn)
        else:
            # Special case for xfp and xpub -- make sure they exist and create if not
            if kn not in self.curr_dict:
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

            return self.curr_dict.get(kn, default)

    def changed(self):
        self.is_dirty += 1
        if self.is_dirty < 2 and self.loop:
            call_later_ms(250, self.write_out())

    def set(self, kn, v):
        # print('Settings: Set {} to {}'.format(kn, to_str(v)))
        if isinstance(v, dict) or self.curr_dict.get(kn, '!~$~!') != v:  # So that None can be set
            self.curr_dict[kn] = v
            self.changed()

    def remove(self, kn):
        self.curr_dict.pop(kn, None)
        # print('Settings: Remove {}'.format(kn))
        self.changed()

    def set_volatile(self, kn, v):
        self.overrides[kn] = v

    def reset(self):
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        # print(' RESET SETTINGS FLASH')
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

        self.flash.erase()
        self.curr_dict = self.default_values()
        self.overrides.clear()
        self.addr = 0
        self.is_dirty = False

    def erase_settings_flash(self):
        self.flash.erase()

    async def write_out(self):
        # delayed write handler
        if not self.is_dirty:
            # someone beat me to it
            return

        # Was sometimes running low on memory in this area: recover
        try:
            import common
            # Don't save settings in the demo loop
            if not common.demo_active:
                gc.collect()
                self.save()
        except MemoryError as e:
            # NOTE: This would be an infinite async loop if it throws an exception every time -- be aware!
            call_later_ms(250, self.write_out())

    def is_erased(self, addr):
        buf = uctypes.bytearray_at(addr, 32)
        for i in range(32):
            if buf[i] != 0xFF:
                return False
        return True

    def find_first_erased_addr(self):
        for addr in SLOT_ADDRS:
            buf = uctypes.bytearray_at(addr, 4)
            if self.is_erased(addr):
                return addr
        return 0

    # We use chunks sequentially since there is no benefit to randomness here.
    def next_addr(self):
        # If no entries were found on load, addr will be zero
        if self.addr == 0:
            addr = self.find_first_erased_addr()
            if addr == 0:
                # Everything is full, so we must erase and start again
                self.flash.erase()
                return SETTINGS_FLASH_START
            else:
                return addr

        # Go to next address
        if self.addr < SETTINGS_FLASH_START + SETTINGS_FLASH_LENGTH - BLOCK_SIZE:
            # Sanity check - if the block we want to write to is not erased, then
            # something has gone wrong and we better erase and start again!
            if not self.is_erased(self.addr + BLOCK_SIZE):
                # print('===============================================================')
                # print('UNERASED MEMORY FOUND AT {}'.format(hex(self.addr)))
                # print('Aborting save')
                # print('===============================================================')
                self.flash.erase()
                return SETTINGS_FLASH_START

            return self.addr + BLOCK_SIZE

        # We reached the end of the bank -- we need to erase it so
        # the new settings can be written.
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        # print(' ERASE WHEN WRAPPING AROUND')
        # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        self.flash.erase()
        return SETTINGS_FLASH_START

    def save(self):
        from export import auto_backup
        # Render as JSON, encrypt and write it
        self.curr_dict['_revision'] = self.curr_dict.get('_revision', 0) + 1

        addr = self.next_addr()

        # print('===============================================================')
        # print('SAVING SETTINGS! _revision={} addr={}'.format(self.curr_dict.get('_revision'), hex(addr)))
        # print('values to save: {}'.format(to_str(self.curr_dict)))
        # print('===============================================================')

        flash_offset = (addr - SETTINGS_FLASH_START) // BLOCK_SIZE
        aes = self.get_aes(flash_offset)

        chk = trezorcrypto.sha256()

        # Create the JSON string as bytes
        json_buf = ujson.dumps(self.curr_dict).encode('utf8')

        # Ensure data is not too big
        if len(json_buf) > DATA_SIZE:
            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            # print(' JSON TOO BIG!')
            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            assert false, 'JSON data is larger than {}.'.format(DATA_SIZE)
            return

        # Create a zero-filled byte buf
        padded_buf = bytearray(DATA_SIZE)

        # Copy the json data into the padded buffer
        for i in range(len(json_buf)):
            padded_buf[i] = json_buf[i]
        del json_buf

        # Add the data and padding to the AES and SHA
        encrypted_buf = aes.encrypt(padded_buf)
        chk.update(padded_buf)

        # Build the final buf for writing to flash
        save_buf = bytearray(BLOCK_SIZE)
        for i in range(len(encrypted_buf)):
            save_buf[i] = encrypted_buf[i]

        digest = chk.digest()
        for i in range(32):
            save_buf[DATA_SIZE + i] = digest[i]

        # print('addr={}\nbuf={}'.format(hex(addr),b2a_hex(save_buf)))
        self.flash.write(addr, save_buf)

        # We don't overwrite the old entry here, even though it's now useless, as that can
        # cause flash to have ECC errors.

        self.addr = addr
        self.is_dirty = 0
        # print("Settings.save(): wrote @ {}".format(hex(addr)))

    def merge(self, prev):
        # take a dict of previous values and merge them into what we have
        self.curr_dict.update(prev)

    @staticmethod
    def default_values():
        # Please try to avoid defaults here. It's better to put into code
        # where value is used, and treat undefined as the default state.

        # _schema indicates what version of settings "schema" is in use
        # Used to help auto-update code that might run after a firmware update.
        return dict(_revision=0, _schema=1)

# EOF
