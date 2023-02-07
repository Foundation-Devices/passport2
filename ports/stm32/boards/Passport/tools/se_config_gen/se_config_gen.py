#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# Determine bits needed to configure ATECC608A for Passport.
#
# Some secrets are configured at factory initialization time, and are then used by
# the secure code in the main firmware.
#

import sys
from secel_config import *
from textwrap import TextWrapper
from contextlib import contextmanager
from binascii import unhexlify as a2b_hex

# Specific slots (aka key numbers) are reserved for specific purposes.


class KEYNUM:
    # reserve 0: it's weird
    pairing_secret = 1  # pairing hash key (picked by bootloader)
    pin_stretch = 2  # secret used to stretch pin (random, forgotten)
    pin_hash = 3  # user-defined PIN to protect the cryptocoins (primary)
    pin_attempt = 4  # secret mixed into pin generation (rate limited, random, forgotten)
    lastgood = 5  # publically readable, PIN required to update: last successful PIN entry (1)
    match_count = 6  # match counter, updated if they get the PIN right
    supply_chain = 7  # Supply chain validation secret value
    seed = 9  # 72 arbitrary bytes protected by main pin (normal case)
    user_fw_pubkey = 10  # Users can load a pubkey so they can load their own firmware which the bootloader will allow
    firmware_timestamp = 11  # Store the most recent officially-signed firmware version to prevent downgrade attacks
    firmware_hash = 14  # hash of flash areas, stored as an unreadable secret, controls GPIO+light
    # reserve 15: non-special, but some fields have all ones and so point to it.


class SEConfig:
    def __init__(self):
        # typical data from a specific virgin chip; serial number and hardware rev will vary!
        self.data = bytearray(a2b_hex('01233b7e00005000e9f5342beec05400c0005500832087208f20c48f8f8f8f8f9f8faf8f0000000000000000000000000000af8fffffffff00000000ffffffff00000000ffffffffffffffffffffffffffffffff00005555ffff0000000000003300330033001c001c001c001c001c003c003c003c003c003c003c003c001c00'))  # nopep8
        assert len(self.data) == 4 * 32 == 128
        self.d_slot = [None] * 16

    def set_slot(self, n, slot_conf, key_conf):
        assert 0 <= n <= 15, n
        assert isinstance(slot_conf, SlotConfig)
        assert 'KeyConfig' in str(type(key_conf))

        self.data[20 + (n * 2): 22 + (n * 2)] = slot_conf.pack()
        self.data[96 + (n * 2): 98 + (n * 2)] = key_conf.pack()

    def set_combo(self, n, combo):
        self.set_slot(n, combo.sc, combo.kc)

    def get_combo(self, n):
        rv = ComboConfig()
        blk = self.data
        rv.kc = KeyConfig.unpack(blk[96 + (2 * n):2 + 96 + (2 * n)])
        rv.sc = SlotConfig.unpack(blk[20 + (2 * n):2 + 20 + (2 * n)])
        return rv

    def set_otp_mode(self, read_only):
        # set OTPmode for consumption or read only
        # default is consumption.
        self.data[18] = 0xAA if read_only else 0x55

    def dump(self):
        secel_dump(self.data)

    def set_gpio_config(self, kn):
        # GPIO is active-high output, controlled by indicated key number
        assert 0 <= kn <= 15
        assert self.data[14] & 1 == 0, "can only work on chip w/ SWI not I2C"
        self.data[16] = 0x1 | (kn << 4)     # "Auth0" mode in table 7-1

    def disable_KdfIvLoc(self):
        # prevent use of weird AES KDF init vector junk
        self.data[72] = 0xf0

    def checks(self):
        # reserved areas / known values
        c = self.data
        assert c[17] == 0               # reserved
        if self.partno == 5:
            assert c[18] in (0xaa, 0x55)    # OTPmode
        assert c[86] in (0x00, 0x55)    # LockValue
        if self.partno == 5:
            assert set(c[90:96]) == set([0])  # RFU, X509Format
        if self.partno == 6:
            assert set(c[92:96]) == set([0])  # RFU, X509Format


class SEConfig608(SEConfig):
    def __init__(self):
        # typical data from a specific virgin chip; serial number and hardware rev will vary!
        self.data = bytearray(a2b_hex('01236c4100006002bbe66928ee015400c0000000832087208f20c48f8f8f8f8f9f8faf8f0000000000000000000000000000af8fffffffff00000000ffffffff000000000000000000000000000000000000000000005555ffff0000000000003300330033001c001c001c001c001c003c003c003c003c003c003c003c001c00'))  # nopep8
        assert len(self.data) == 4 * 32 == 128
        self.d_slot = [None] * 16
        self.partno = 6

    def counter_match(self, kn):
        assert 0 <= kn <= 15
        self.data[18] = (kn << 4) | 0x1

    @contextmanager
    def chip_options(self):
        co = ChipOptions.unpack(self.data[90:92])
        yield co
        self.data[90:92] = co.pack()


def cpp_dump_hex(buf):
    # format for CPP macro
    txt = ', '.join('0x%02x' % i for i in buf)
    tw = TextWrapper(width=60)
    return '\n'.join('\t%s   \\' % i for i in tw.wrap(txt))


def main():
    with open('../../include/se-config.h', 'wt') as fp:
        print('// Autogenerated; see tools/se_config_gen\n', file=fp)

        doit(SEConfig608(), fp)


def doit(se, fp):
    # default all slots to storage
    cfg = [ComboConfig() for i in range(16)]
    for j in range(16):
        cfg[j].for_storage()

    # unique keys per-device
    # - pairing key for linking SE and main micro together
    # - critical!
    cfg[KEYNUM.pairing_secret].hash_key().lockable(False)

    secure_map = [
        (KEYNUM.pin_hash, KEYNUM.seed, KEYNUM.lastgood)
    ]

    unused_slots = [0, 8, 12, 13, 15]

    # new slots related to pin attempt- and rate-limiting
    # - both hold random, unknown contents, can't be changed
    # - use of the first one will cost a counter incr
    # - actual PIN to be used is rv=HMAC(pin_stretch, rv) many times
    cfg[KEYNUM.pin_attempt].hash_key().require_auth(KEYNUM.pairing_secret).deterministic().limited_use()

    # to rate-limit PIN attempts (also used for prefix words) we require
    # many HMAC cycles using this random+unknown value.
    cfg[KEYNUM.pin_stretch].hash_key().require_auth(KEYNUM.pairing_secret).deterministic()

    # chip-enforced pin attempts: link keynum and enable "match count" feature
    cfg[KEYNUM.match_count].writeable_storage(KEYNUM.pin_hash).require_auth(KEYNUM.pairing_secret)
    se.counter_match(KEYNUM.match_count)

    # User firmware installation pubkey - updatable with PIN, readable with just the pairing secret
    cfg[KEYNUM.user_fw_pubkey].writeable_storage(KEYNUM.pin_hash).require_auth(KEYNUM.pairing_secret)

    # Supply chain secret
    cfg[KEYNUM.supply_chain].hash_key().require_auth(KEYNUM.pairing_secret).deterministic()

    # turn off selftest feature (performance problem), and enforce encryption
    # (io protection) for verify, etc.
    with se.chip_options() as opt:
        opt.POSTEnable = 0
        opt.IOProtKeyEnable = 1
        opt.ECDHProt = 0x1      # allow encrypted output
        opt.KDFProt = 0x1       # allow encrypted output
        opt.IOProtKey = KEYNUM.pairing_secret

    # don't want
    se.disable_KdfIvLoc()

    # PIN and corresponding protected secrets
    # - if you know old value of PIN, you can write it (to change to new PIN)
    for kn, sec_num, lg_num in secure_map:
        cfg[kn].hash_key(write_kn=kn).require_auth(KEYNUM.pairing_secret)
        cfg[sec_num].secret_storage(kn).require_auth(kn)
        if lg_num is not None:
            # used to hold counter0 value when we last successfully got that PIN
            cfg[lg_num].writeable_storage(kn).require_auth(KEYNUM.pairing_secret)

    # Timestamp of the last officially-signed firmware that was installed.
    # Bootloader will not install any firmware with a timestamp older than this value.
    # Unlike KEYNUM.firmware_hash, this slot needs to be readable by the bootloader.
    cfg[KEYNUM.firmware_timestamp].secret_storage(KEYNUM.firmware_hash).require_auth(KEYNUM.pairing_secret)

    # Hash based on a combination of hardware IDs and the firmware hash
    # - Blue light is controlled by setting this value at boot
    cfg[KEYNUM.firmware_hash].secret_storage(KEYNUM.firmware_hash).no_read().require_auth(KEYNUM.pairing_secret)

    # Slot 8 is special because its data area is larger and could hold a
    # certificate in DER format. All the others are 36/72 bytes only
    assert cfg[8].kc.KeyType == 7

    # Slot 0 has baggage because a zero value for ReadKey has special meaning,
    # so avoid using it. But had to put something in ReadKey, so it's 15 sometimes.
    assert cfg[0].sc.IsSecret == 0
    assert cfg[15].sc.IsSecret == 0

    assert len(cfg) == 16
    for idx, x in enumerate(cfg):
        # no EC keys on this project
        assert cfg[idx].kc.KeyType in [6, 7], idx

        print('Processing slot {}'.format(idx))

        if idx == KEYNUM.pairing_secret:
            assert cfg[idx].kc.KeyType == 7
        elif idx == KEYNUM.supply_chain:
            # Unreadable/unwritable
            pass
        elif idx in unused_slots:
            # check not used
            assert cfg[idx].sc.as_int() == 0x0000, idx
            assert cfg[idx].kc.as_int() == 0x003c, idx
        else:
            # Use of **any** key requires knowledge of pairing secret
            # except PIN-protected slots, which require PIN (which requires pairing secret)
            assert cfg[idx].kc.ReqAuth, idx
            assert (cfg[idx].kc.AuthKey == KEYNUM.pairing_secret) or \
                (cfg[cfg[idx].kc.AuthKey].kc.AuthKey == KEYNUM.pairing_secret), idx

        se.set_combo(idx, cfg[idx])

    # require CheckMac on indicated key to turn on GPIO
    se.set_gpio_config(KEYNUM.firmware_hash)

    se.checks()

    # se.dump()

    # generate a single header file we will need
    if fp:
        print('// bytes [16..84) of chip config area', file=fp)
        print('#define SE_CHIP_CONFIG_1 { \\', file=fp)
        print(cpp_dump_hex(se.data[16:84]), file=fp)
        print('}\n\n', file=fp)

        print('// bytes [90..128) of chip config area', file=fp)
        print('#define SE_CHIP_CONFIG_2 { \\', file=fp)
        print(cpp_dump_hex(se.data[90:]), file=fp)
        print('}\n\n', file=fp)

        print('// key/slot usage and names', file=fp)
        names = [nm for nm in dir(KEYNUM) if nm[0] != '_']
        for v, nm in sorted((getattr(KEYNUM, nm), nm) for nm in names):
            print('#define KEYNUM_%-20s\t%d' % (nm.lower(), v), file=fp)

        print('\n/*\n', file=fp)
        sys.stdout = fp
        se.dump()
        print('\n*/', file=fp)


if __name__ == '__main__':
    main()
