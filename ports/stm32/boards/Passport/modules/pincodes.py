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
import ustruct
from callgate import get_anti_phishing_words, get_supply_chain_validation_words
from ubinascii import hexlify as b2a_hex
from se_commands import *
import common

# See ../stm32/bootloader/pins.h for source of these constants.
#
MAX_PIN_LEN = const(32)

# how many bytes per secret (you don't have to use them all)
SE_SECRET_LEN = const(72)

# magic number for struct
PA_MAGIC_V1 = const(0xc50b61a7)

# For state_flags field: report only covers current wallet (primary vs. secondary)
PA_SUCCESSFUL = const(0x01)
PA_IS_BLANK = const(0x02)
PA_HAS_DURESS = const(0x04)
PA_HAS_BRICKME = const(0x08)
PA_ZERO_SECRET = const(0x10)

# For change_flags field:
CHANGE_WALLET_PIN = const(0x001)
CHANGE_DURESS_PIN = const(0x002)
CHANGE_BRICKME_PIN = const(0x004)
CHANGE_SECRET = const(0x008)
CHANGE_DURESS_SECRET = const(0x010)
# CHANGE_SECONDARY_WALLET_PIN = const(0x020)
CHANGE_LS_OFFSET = const(0xf00)

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

# just a few of the likely ones; non-programming errors
EPIN_I_AM_BRICK = const(-105)
EPIN_MUST_WAIT = const(-107)
EPIN_PIN_REQUIRED = const(-108)
EPIN_WRONG_SUCCESS = const(-109)
EPIN_OLD_ATTEMPT = const(-110)
EPIN_AUTH_FAIL = const(-112)
EPIN_OLD_AUTH_FAIL = const(-113)

# We are round-tripping this big structure, partially signed by bootloader.
'''
    uint32_t    magic_value;            // = PA_MAGIC_V1
    char        pin[MAX_PIN_LEN];       // value being attempted
    int         pin_len;                // valid length of pin
    uint32_t    delay_achieved;         // so far, how much time wasted? [508a only]
    uint32_t    delay_required;         // how much will be needed? [508a only]
    uint32_t    num_fails;              // for UI: number of fails PINs
    uint32_t    attempts_left;          // trys left until bricking [608a only]
    uint32_t    state_flags;            // what things have been setup/enabled already
    uint32_t    private_state;          // some internal (encrypted) state
    uint8_t     hmac[32];               // bootloader's hmac over above, or zeros
    // remaining fields are return values, or optional args;
    int         change_flags;           // bitmask of what to do
    char        old_pin[MAX_PIN_LEN];   // (optional) old PIN value
    int         old_pin_len;            // (optional) valid length of old_pin, can be zero
    char        new_pin[MAX_PIN_LEN];   // (optional) new PIN value
    int         new_pin_len;            // (optional) valid length of new_pin, can be zero
    uint8_t     secret[72];             // secret to be changed OR return value
    uint8_t     cached_main_pin[32];    // iff they provided right pin already (V2)
'''
PIN_ATTEMPT_FMT_V1 = 'I32si6I32si32si32si72s32s'
PIN_ATTEMPT_SIZE_V1 = const(276)


class BootloaderError(RuntimeError):
    pass


class PinAttempt:
    seconds_per_tick = 0.5

    def __init__(self):
        self.pin = None
        self.secret = None
        self.is_empty = None
        self.magic_value = PA_MAGIC_V1
        self.delay_achieved = 0         # so far, how much time wasted?
        self.delay_required = 0         # how much will be needed?
        self.num_fails = 0              # for UI: number of fails PINs
        self.attempts_left = 0          # ignore in mk1/2 case, only valid for mk3
        self.max_attempts = 21          # Numbger of attempts allowed
        self.state_flags = 0            # useful readback
        self.private_state = 0          # opaque data, but preserve
        self.cached_main_pin = bytearray(32)
        self.is_logged_in = False

        assert MAX_PIN_LEN == 32        # update FMT otherwise
        assert ustruct.calcsize(PIN_ATTEMPT_FMT_V1) == PIN_ATTEMPT_SIZE_V1, \
            ustruct.calcsize(PIN_ATTEMPT_FMT_V1)

        self.buf = bytearray(PIN_ATTEMPT_SIZE_V1)

        # check for bricked system early
        import callgate
        if callgate.get_is_bricked():
            # die right away if it's not going to work
            # print('I AM I BRICKED!!!')
            pass

    def __repr__(self):
        return '<PinAttempt: num_fails={} delay={}/{} attempts_left={} state=0x{} hmac={}>'.format(
            self.num_fails,
            self.delay_achieved, self.delay_required, self.attempts_left, hex(self.state_flags),
            b2a_hex(self.hmac))

    def marshal(self, msg, new_secret=None, new_pin=None, old_pin=None, ls_offset=None):
        # serialize our state, and maybe some arguments
        change_flags = 0

        if new_secret is not None:
            change_flags |= CHANGE_SECRET
            assert len(new_secret) in (32, SE_SECRET_LEN)
        else:
            new_secret = bytes(SE_SECRET_LEN)

        # NOTE: pins should be bytes here.

        if new_pin is not None:
            change_flags |= CHANGE_WALLET_PIN
            assert not old_pin or old_pin == self.pin
            old_pin = self.pin

            assert len(new_pin) <= MAX_PIN_LEN
            assert old_pin is not None
            assert len(old_pin) <= MAX_PIN_LEN
        else:
            new_pin = b''
            old_pin = old_pin if old_pin is not None else self.pin

        if ls_offset is not None:
            change_flags |= (ls_offset << 8)        # see CHANGE_LS_OFFSET

        # can't send the V2 extra stuff if the bootrom isn't expecting it
        fields = [self.magic_value,
                  self.pin,
                  len(self.pin),
                  self.delay_achieved,
                  self.delay_required,
                  self.num_fails,
                  self.attempts_left,
                  self.state_flags,
                  self.private_state,
                  self.hmac,
                  change_flags,
                  old_pin,
                  len(old_pin),
                  new_pin,
                  len(new_pin),
                  new_secret,
                  self.cached_main_pin]

        fmt = PIN_ATTEMPT_FMT_V1

        ustruct.pack_into(fmt, msg, 0, *fields)

    def unmarshal(self, msg):
        # unpack it and update our state, return other state
        x = ustruct.unpack_from(PIN_ATTEMPT_FMT_V1, msg)

        (self.magic_value,
         self.pin,
         pin_len,
         self.delay_achieved,
         self.delay_required,
         self.num_fails,
         self.attempts_left,
         self.state_flags,
         self.private_state,
         self.hmac,
         change_flags,
         old_pin,
         old_pin_len,
         new_pin,
         new_pin_len,
         secret,
         self.cached_main_pin) = x

        # NOTE: not useful to readback values we sent and it never updates
        # new_pin = new_pin[0:new_pin_len]
        # old_pin = old_pin[0:old_pin_len]
        self.pin = self.pin[0:pin_len]

        return secret

    def pin_control(self, method_num, **kws):

        self.marshal(self.buf, **kws)

        # print("> tx: %s" % b2a_hex(self.buf))

        err = common.system.dispatch(CMD_PIN_CONTROL, self.buf, method_num)

        # print("[%d] rx: %s" % (err, b2a_hex(self.buf)))

        if err <= -100:
            # print("[%d] req: %s" % (err, b2a_hex(self.buf)))
            if err == EPIN_I_AM_BRICK:
                raise RuntimeError(err)

            # Unpack the updated attempts_left and num_fails if the pin was wrong so the UI updates correctly
            if err == EPIN_AUTH_FAIL:
                self.unmarshal(self.buf)
                # print('Unmarshalled: {}'.format(self.attempts_left))

            # print('ERROR: {} ({})'.format(PA_ERROR_CODES[err], err))
            raise BootloaderError(PA_ERROR_CODES[err], err)
        elif err:
            raise RuntimeError(err)

        return self.unmarshal(self.buf)

    @staticmethod
    def anti_phishing_words(pin_prefix):
        # Take a prefix of the PIN and turn it into two
        # bip39 words for anti-phishing protection.
        assert 1 <= len(pin_prefix) <= MAX_PIN_LEN, len(pin_prefix)

        padding = MAX_PIN_LEN - len(pin_prefix)
        buf = bytearray(pin_prefix) + b'\0' * padding
        err = get_anti_phishing_words(buf)
        if err:
            raise RuntimeError(err)

        # Get a mnemonic from the 32 bytes in the buffer
        s = trezorcrypto.bip39.from_data(buf)
        rv = s.split()

        return rv[0:2]  # Only keep 2 words for anti-phishing prefix

    @staticmethod
    def supply_chain_validation_words(challenge_str):
        # Take the validation string and turn it into 4
        # bip39 words for supply chain tampering detection.

        # print('challenge_str={}'.format(challenge_str))
        buf = bytearray(challenge_str)

        # This actually gets the HMAC bytes, not the words
        err = get_supply_chain_validation_words(buf)
        if err:
            raise RuntimeError(err)
        # print('hmac buf = {}'.format(buf))

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
        # device has no PIN at this point
        return bool(self.state_flags & PA_IS_BLANK)

    def is_successful(self):
        # we've got a valid pin
        # print('self.state_flags = {:04x}'.format(self.state_flags))
        return bool(self.state_flags & PA_SUCCESSFUL)

    def is_secret_blank(self):
        # assert self.state_flags & PA_SUCCESSFUL
        return bool(self.state_flags & PA_ZERO_SECRET)

    def reset(self):
        # start over, like when you commit a new seed
        return self.setup(self.pin)

    # Prepare the class for a PIN operation (first pin, login, change)
    def setup(self, pin):
        # print('Setting up SE hmac')
        self.pin = pin
        self.hmac = bytes(32)

        _ = self.pin_control(PIN_SETUP)

        return self.state_flags

    def login(self):
        # test we have the PIN code right, and unlock access if so.
        chk = self.pin_control(PIN_ATTEMPT)
        self.is_empty = (chk[0] == 0)

        ok = self.is_successful()

        self.is_logged_in = ok

        return ok

    def change(self, **kws):
        # change various values, stored in secure element
        self.pin_control(PIN_CHANGE, **kws)

        # IMPORTANT:
        # - call new_main_secret() when main secret changes!
        # - is_secret_blank and is_successful may be wrong now, re-login to get again

    def fetch(self):
        secret = self.pin_control(PIN_GET_SECRET)
        return secret

    async def new_main_secret(self, raw_secret, chain=None):
        from common import settings, flash_cache
        import stash

        # Recalculate xfp/xpub values (depends both on secret and chain)
        with stash.SensitiveValues(raw_secret) as sv:
            if chain is not None:
                sv.chain = chain
            sv.capture_xpub()

        # We shouldn't need to save this anymore since we are dynamically managing xfp and xpub
        # settings.save()

        # Set the key for the flash cache (cache was inaccessible prior to user logging in)
        flash_cache.set_key(new_secret=raw_secret)

        # Need to save out flash cache with the new secret or else we won't be able to read it back later
        flash_cache.save()

# EOF
