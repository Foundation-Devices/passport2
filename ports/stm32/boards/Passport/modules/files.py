# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# files.py - microSD and related functions.
#

import passport
import pyb
import os
import sys
import utime
from uerrno import ENODEV, ENOENT


def _try_microsd(bad_fs_ok=False):
    from common import system

    sd_root = system.get_sd_root()

    # Power up, mount the SD card, return False if we can't for some reason.
    #
    # If we're about to reformat, we don't need a working filesystem

    sd = pyb.SDCard()

    if not sd.present():
        return False

    if passport.IS_SIMULATOR:
        return True

    try:
        # already mounted and ready?
        st = os.statvfs(sd_root)
        return True
    except OSError as exc:
        # ENODEV in this case means that the SD card is not mounted, but
        # present.
        if exc.args[0] != ENODEV:
            return False

    try:
        sd.power(1)
        os.mount(sd, sd_root, readonly=0, mkfs=0)
        st = os.statvfs(sd_root)

        return True

    except OSError as exc:
        # corrupt or unformated SD card (or something)
        if bad_fs_ok:
            return True
        # sys.print_exception(exc)
        return False


class CardMissingError(RuntimeError):
    pass


class CardSlot:
    # Touch interface must be disabled during any SD Card usage!
    last_change = None
    sd_card_change_cb = None

    @classmethod
    def setup(cls):
        # Watch the SD card-detect signal line... but very noisy
        # - this is called a few seconds after system startup

        from pyb import Pin, ExtInt

        def card_change(_):
            # Careful: these can come fast and furious!
            cls.last_change = utime.ticks_ms()

            if cls.sd_card_change_cb is not None:
                cls.sd_card_change_cb()

        cls.last_change = utime.ticks_ms()

        cls.irq = ExtInt(Pin('SD_SW'), ExtInt.IRQ_RISING_FALLING,
                         Pin.PULL_UP, card_change)

    @classmethod
    def get_sd_root(cls):
        from common import system
        return system.get_sd_root()

    @classmethod
    def get_sd_card_change_cb(cls):
        return cls.sd_card_change_cb

    @classmethod
    def set_sd_card_change_cb(cls, sd_card_change_cb):
        cls.sd_card_change_cb = sd_card_change_cb

    def __init__(self):
        self.active = False

    def __enter__(self):
        # Get ready!

        # busy wait for card pin to debounce/settle
        while True:
            since = utime.ticks_diff(utime.ticks_ms(), self.last_change)
            if since > 50:
                break
            utime.sleep_ms(5)

        # attempt to use micro SD
        ok = _try_microsd()

        if not ok:
            self.recover()

            raise CardMissingError

        self.active = True

        return self

    def __exit__(self, *a):
        self.recover()
        return False

    def recover(self):
        from common import system
        sd_root = system.get_sd_root()

        self.active = False

        try:
            os.umount(sd_root)
        except BaseException:
            pass

        # important: turn off power so touch can work again
        sd = pyb.SDCard()
        sd.power(0)

    def get_paths(self):
        # (full) paths to check on the card
        root = self.get_sd_root()

        return [root]

    def pick_filename(self, pattern, path=None):
        # given foo.txt, return a full path to filesystem, AND
        # a nice shortened version of the filename for display to user
        # - assuming we will write to it, so cannot exist
        # - return None,None if no SD card or can't mount, etc.
        # - no UI here please
        import ure
        import uos

        assert self.active      # used out of context mgr

        # prefer SD card if we can
        path = path or (self.get_sd_root())

        assert '/' not in pattern, "Filenames must not contain '/'"
        assert '.' in pattern, "Filenames must have an extension like '.txt'"

        basename, ext = pattern.rsplit('.', 1)
        ext = '.' + ext

        # rename numberless first
        numberless_fname = path + '/' + basename + ext
        fname = path + '/' + basename + '-001' + ext
        try:
            os.stat(numberless_fname)
            uos.rename(numberless_fname, fname)
        except OSError as e:
            pass  # file doesn't exist, move on

        # look for existing numbered files, even if some are deleted, and pick next
        # highest filename
        highest = 0
        pat = ure.compile(basename + r'-(\d+)' + ext)

        files = uos.ilistdir(path)
        for fn, *var in files:
            m = pat.match(fn)
            if not m:
                continue

            # Rename older files to fit 3 digit numbering scheme
            old_num = int(m.group(1))
            new_fn = basename + ('-%03d' % old_num) + ext
            if fn != new_fn:
                uos.rename(path + '/' + fn, path + '/' + new_fn)

            highest = max(highest, old_num)

        fname = path + '/' + basename + ('-%03d' % (highest + 1)) + ext

        return fname, fname[len(path):]

    @classmethod
    def get_file_path(self, filename, path=None):
        # given foo.txt, return a full path to filesystem, AND
        # a nice shortened version of the filename for display to user

        path = path or (self.get_sd_root() + '/')

        assert '/' not in filename
        assert '.' in filename

        basename, ext = filename.rsplit('.', 1)
        ext = '.' + ext

        fname = path + basename + ext

        return fname, basename + ext


def securely_blank_file(full_path):
    # input PSBT file no longer required; so delete it
    # - blank with zeros
    # - rename to garbage (to hide filename after undelete)
    # - delete
    # - ok if file missing already (card maybe have been swapped)
    #
    # NOTE: we know the FAT filesystem code is simple, see
    #       ../external/micropython/extmod/vfs_fat.[ch]

    path, basename = full_path.rsplit('/', 1)

    with CardSlot() as card:
        try:
            blk = bytes(64)

            with open(full_path, 'r+b') as fd:
                size = fd.seek(0, 2)
                fd.seek(0)

                # blank it
                for i in range((size // len(blk)) + 1):
                    fd.write(blk)

                assert fd.seek(0, 1) >= size

            # probably pointless, but why not:
            if not passport.IS_SIMULATOR:
                os.sync()

        except OSError as exc:
            # missing file is okay
            if exc.args[0] == ENOENT:
                return
            raise

        # rename it and delete
        new_name = path + '/' + ('x' * len(basename))
        os.rename(full_path, new_name)
        os.remove(new_name)
# EOF
