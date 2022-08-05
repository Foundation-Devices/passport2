# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# pincodes.py - manage PIN code (which map to wallet seeds)
#

import trezorcrypto
from callgate import get_anti_phishing_words, get_supply_chain_validation_words
from ubinascii import hexlify as b2a_hex, unhexlify as a2b_hex
from se_commands import *
import common

# See ../stm32/bootloader/pins.h for source of these constants.
#
MAX_PIN_LEN = const(32)

# How many bytes per secret (you don't have to use them all)
SE_SECRET_LEN = const(72)

MAX_PIN_ATTEMPTS = 21
ZERO_SECRET = (b'\x00' * 72)
ZERO_SECRET_STR = b2a_hex(b'\x00' * 72).decode('utf-8')

# See below for other direction as well.
PA_ERROR_CODES = {
    -100: "HMAC_FAIL",
    -101: "HMAC_REQUIRED",
    -102: "BAD_MAGIC",
    -103: "RANGE_ERR",
    -104: "BAD_REQUEST",
    -105: "I_AM_BRICK",
    -106: "SE_FAIL",
    -107: "MUST_WAIT",
    -108: "PIN_REQUIRED",
    -109: "WRONG_SUCCESS",
    -110: "OLD_ATTEMPT",
    -111: "AUTH_MISMATCH",
    -112: "AUTH_FAIL",
    -113: "OLD_AUTH_FAIL",
    -114: "PRIMARY_ONLY",
}

# just a few of the likely ones; non-programing errors
EPIN_I_AM_BRICK = const(-105)
EPIN_AUTH_FAIL = const(-112)


class BootloaderError(RuntimeError):
    pass


class PinAttempt:
    def __init__(self):
        self.pin = None
        self.secret = None
        self.attempts_left = 0          # ignore in mk1/2 case, only valid for mk3
        self.max_attempts = MAX_PIN_ATTEMPTS          # Number of attempts allowed
        self.num_fails = 0
        self.is_logged_in = False

    def __repr__(self):
        return '<PinAttempt: pin={}, secret={}, attempts_left={}>'.format(
            self.pin,
            self.secret,
            self.attempts_left)

    def pin_control(self, method_num, **kwargs):
        from common import settings
        err = 0

        if method_num == PIN_GET_SECRET:
            self.load_secret()
            err = 0

        else:
            err = -100

        # Handle "result" from above
        if err <= -100:
            # print("[%d] req: %s" % (err, b2a_hex(self.buf)))
            if err == EPIN_I_AM_BRICK:
                raise RuntimeError(EPIN_AUTH_FAIL)

            # print('ERROR: {} ({})'.format(PA_ERROR_CODES[err], err))
            raise BootloaderError(PA_ERROR_CODES[err], err)
        elif err:
            raise RuntimeError(err)

        return self.secret

    @staticmethod
    def anti_phishing_words(pin_prefix):
        import foundation

        # Take a prefix of the PIN and turn it into two
        # bip39 words for anti-phishing protection.
        assert 1 <= len(pin_prefix) <= MAX_PIN_LEN, len(pin_prefix)

        padding = MAX_PIN_LEN - len(pin_prefix)
        buf = bytearray(pin_prefix) + b'\0' * padding
        foundation.sha256(buf, buf)

        # Get a mnemonic from the 32 bytes in the buffer
        s = trezorcrypto.bip39.from_data(buf)
        rv = s.split()

        return rv[0:2]  # Only keep 2 words for anti-phishing prefix

    # NOTE: This code does NOT calculate a valid supply chain response, as that
    #       would require exposing the secret used for the HMAC.
    @ staticmethod
    def supply_chain_validation_words(challenge_str):
        # Take the validation string and turn it into 4
        # bip39 words for supply chain tampering detection.

        # print('challenge_str={}'.format(challenge_str))
        buf = bytearray(challenge_str)

        # This actually gets the HMAC bytes, not the words
        for i in range(32):
            buf[i] = 0

        # Get a mnemonic from the 32 bytes in the buffer
        buf = buf[:32]
        if len(buf) < 32:
            padding = 32 - len(buf)
            buf = buf + b'\0' * padding

        s = trezorcrypto.bip39.from_data(buf)
        rv = s.split()
        # print('supply chain validation words = {}'.format(rv[0:4]))

        return rv[0:4]  # Only keep 4 words for supply chain validation

    def is_blank(self):
        self.pin = common.settings.get('__pin__', '')
        pin = common.settings.get('__pin__', '')
        return pin == ''

    def is_successful(self):
        # print('self.state_flags = {:04x}'.format(self.state_flags))
        return self.is_logged_in

    def is_secret_blank(self):
        from common import settings
        self.load_secret()
        # print('self.secret = {}'.format(self.secret))
        return self.secret == ZERO_SECRET

    def reset(self):
        # start over, like when you commit a new seed
        return self.setup(self.pin)

    # Prepare the class for a PIN operation (first pin, login, change)
    def setup(self, pin, secondary=False):
        from common import settings
        # print('Setting up pin for login attempt')
        self.pin = pin
        self.attempts_left = settings.get(
            '__attempts_left__', MAX_PIN_ATTEMPTS)

        return 0

    def login(self):
        from common import settings
        curr_pin = settings.get('__pin__', '')
        self.is_logged_in = False

        # print('login(): self.pin={}, curr_pin={}'.format(self.pin, curr_pin))
        pins_match = self.pin == curr_pin
        if not pins_match:
            # print('PIN mismatch!')
            if self.attempts_left > 0:
                self.attempts_left -= 1
                self.num_fails += 1
                if self.attempts_left > MAX_PIN_ATTEMPTS:
                    self.attempts_left = MAX_PIN_ATTEMPTS
                settings.set('__attempts_left__', self.attempts_left)
                raise RuntimeError()
        else:
            # Reset to 21 when successfully logged in
            self.attempts_left = MAX_PIN_ATTEMPTS
            self.is_logged_in = True
            settings.set('__attempts_left__', MAX_PIN_ATTEMPTS)

        return self.is_logged_in

    def change(self, **kwargs):
        from common import settings
        from utils import is_all_zero

        new_secret = kwargs.get('new_secret', None)
        if new_secret == None:
            curr_pin = settings.get('__pin__', '').encode()
            old_pin = kwargs.get('old_pin', '').encode()
            new_pin = kwargs.get('new_pin', '').encode()

            # print('PIN_CHANGE: curr_pin={} old_pin={} new_pin={}'.format(curr_pin, old_pin, new_pin))
            if old_pin != curr_pin:
                raise ValueError

            # print('new_pin={}, len={}'.format(new_pin, len(new_pin)))
            if isinstance(new_pin, (bytes, bytearray)) and is_all_zero(new_pin):
                # print('RECEIVED BLANK PIN!')
                settings.set('__pin__', '')
            else:
                settings.set('__pin__', new_pin.decode())

            # We have to save because the caller tries to reset before the normal save timeout expires
            settings.save()

        else:
            # print('change(): {}'.format(new_secret))
            self.save_secret(new_secret)

    def save_secret(self, buf):
        from common import settings
        str = b2a_hex(buf).decode('utf-8')
        # print('save_secret: {}'.format(str))
        settings.set('__secret__', str)
        settings.save()
        self.load_secret()

    def load_secret(self):
        from common import settings
        str = settings.get('__secret__', ZERO_SECRET_STR)
        self.secret = a2b_hex(str.encode('utf-8'))

    def fetch(self):
        from common import settings
        self.load_secret()
        return self.secret

    async def new_main_secret(self, raw_secret, chain=None):
        from common import settings, flash_cache
        import stash

        # Recalculate xfp/xpub values (depends both on secret and chain)
        with stash.SensitiveValues(raw_secret) as sv:
            if chain is not None:
                sv.chain = chain
            sv.capture_xpub()

        # TODO: Is this comment still accurate?
        # We shouldn't need to save this anymore since we are dynamically managing xfp and xpub
        # settings.save()

        # Set the key for the flash cache (cache was inaccessible prior to user logging in)
        flash_cache.set_key(new_secret=raw_secret)

        # Need to save out flash cache with the new secret or else we won't be able to read it back later
        flash_cache.save()

# EOF
