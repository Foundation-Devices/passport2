# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# settings.py - Simulator settings - simplified and not encrypted


import ujson
from uio import BytesIO
from utils import call_later_ms

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


class Settings:

    def __init__(self, loop=None, serial=None):
        from common import system  # This is defined before Settings is created, so OK to use here

        self.loop = loop
        self.is_dirty = 0

        # AES key is based on the serial number now instead of the PIN
        # We don't store anything critical in the settings, so this level of protection is fine,
        # and avoids having 2 sets of settings (one with a zero AES key and one with the PIN-based key).
        serial = system.get_serial_number()
        # print('Settings: serial={}'.format(serial))
        # print('Settings: aes_key={}'.format(self.aes_key))

        self.curr_dict = self.default_values()
        self.overrides = {}     # volatile overide values

        self.load()

    def load(self):
        # reset
        self.curr_dict.clear()
        self.overrides.clear()
        self.addr = 0
        self.is_dirty = 0

        try:
            b = open('settings.json', 'rb').read()
            self.curr_dict = ujson.load(BytesIO(b))
            # print('settings.json={}'.format(self.curr_dict))
        except:
            pass
            # print('ERROR: Unable to decode work/settings.json file')

    def save(self):
        # Render as JSON, encrypt and write it
        self.curr_dict['_revision'] = self.curr_dict.get('_revision', 0) + 1

        # Simple save to JSON file
        with open('settings.json', 'w') as f:
            json_buf = ujson.dumps(self.curr_dict).encode('utf8')
            f.write(json_buf)
            self.is_dirty = False

    def get(self, kn, default=None):
        if kn in self.overrides:
            return self.overrides.get(kn)
        else:
            # Special case for xfp and xpub -- make sure they exist and create if not
            if kn not in self.curr_dict:
                if kn == 'xfp' or kn == 'xpub':
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

        self.curr_dict = self.default_values()
        self.overrides.clear()
        self.addr = 0
        self.is_dirty = False

    async def write_out(self):
        import common

        # delayed write handler
        if not self.is_dirty:
            # someone beat me to it
            return

        # Don't save settings in the demo loop
        if not common.demo_active:
            self.save()

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
