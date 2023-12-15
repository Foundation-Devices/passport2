# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# SPDX-FileCopyRightText: 2019 cryptoadvance
# SPDX-License-Identifier: MIT
#
# utils.py
#

import lvgl as lv
from constants import NUM_BACKUP_CODE_SECTIONS, NUM_DIGITS_PER_BACKUP_CODE_SECTION
from public_constants import DIR_BACKUPS
from files import CardSlot
from styles.colors import DEFAULT_LARGE_ICON_COLOR
import ustruct
import uos
import trezorcrypto
import stash
from ubinascii import hexlify as b2a_hex
from ubinascii import unhexlify as a2b_hex
from ubinascii import a2b_base64, b2a_base64
from uasyncio import get_event_loop, sleep_ms
import common
import passport

ENABLE_LOGGING = True


def log(*args, **kwargs):
    global ENABLE_LOGGING
    if ENABLE_LOGGING:
        print(*args, **kwargs)


def read_user_firmware_pubkey():
    from common import system
    pubkey = bytearray(64)

    result = system.get_user_firmware_pubkey(pubkey)

    return result, pubkey

# We cache this here to avoid slowing down the menus, since the menu items in the Developer Pubkey
# menu look up this value to decide when to become visible/hidden.


def has_dev_pubkey():
    if common.cached_pubkey is None:
        result, common.cached_pubkey = read_user_firmware_pubkey()
        if not result:
            return False
    return not is_all_zero(common.cached_pubkey)


def clear_cached_pubkey():
    common.cached_pubkey = None


def is_all_zero(buf):
    for b in buf:
        if b != 0:
            return False
    return True


def time_now_ms():
    import utime
    return utime.ticks_ms()


# Lookup version number from header
def get_fw_version():
    # TODO: Implement version number function
    return '2020-08-30', '0.1.0', '???'


def start_task(task):
    loop = get_event_loop()
    return loop.create_task(task)


async def spinner_task(text, task, args=(), left_micron=None, right_micron=None, min_duration_ms=1000, no_anim=False):
    from pages import SpinnerPage, StatusPage
    from uasyncio import sleep_ms
    from utime import ticks_ms
    from common import ui

    # Disable left/right navigation and icons
    prev_top_level = ui.set_is_top_level(False)

    start_time = ticks_ms()
    if no_anim:
        spinner = StatusPage(text, left_micron=left_micron, right_micron=right_micron,
                             icon=lv.LARGE_ICON_STATIC_PIN_SPINNER, icon_color=DEFAULT_LARGE_ICON_COLOR)
    else:
        spinner = SpinnerPage(text, left_micron=left_micron, right_micron=right_micron)

    task_result = None

    # User can pass a variable number of arguments, which we return as the result
    async def on_done(*args):
        # print('on_done() args="{}"'.format(args))
        nonlocal task_result
        task_result = args

        # The last arg is always the error
        error = args[-1] if len(args) > 0 else None

        # Enforce minimum delay so that the message is at least briefly seed
        end_time = ticks_ms()
        if end_time - start_time < min_duration_ms:
            await sleep_ms(min_duration_ms - (end_time - start_time))

        ui.set_is_top_level(prev_top_level)

        spinner.set_result(error is None)

    start_task(task(on_done, *args))

    # Can handle the user pressing a key here by just showing the spinner again
    while True:
        await spinner.show()
        if task_result is not None:
            break

    return task_result


def call_later_ms(delay_ms, coro):
    async def delay_fn():
        await sleep_ms(delay_ms)
        await coro

    loop = get_event_loop()
    loop.create_task(delay_fn())


def save_error_log(msg, filename):
    from files import CardSlot

    wrote_to_sd = False
    try:
        with CardSlot() as card:
            # Full path and short filename
            fname, _ = card.get_file_path(filename)
            with open(fname, 'wb') as fd:
                fd.write(msg)
                wrote_to_sd = True
    except Exception:
        return wrote_to_sd

    return wrote_to_sd


async def save_error_log_to_microsd_task(msg, filename):
    import common

    sd_card_change = False

    def sd_card_cb():
        nonlocal sd_card_change

        if not sd_card_change:
            sd_card_change = True

    # Activate SD card hook
    CardSlot.set_sd_card_change_cb(sd_card_cb)

    while True:
        if sd_card_change:
            sd_card_change = False
            saved = save_error_log(msg, filename)
            if saved:
                common.ui.set_card_header(title='Saved to microSD', icon='ICON_MICROSD')

        await sleep_ms(100)


def handle_fatal_error(exc):
    import common
    from styles.colors import BLACK
    from pages import LongTextPage
    from flows import PageFlow
    import microns
    from tasks import card_task

    import sys
    sys.print_exception(exc)
    # if isinstance(exc, KeyboardInterrupt):
    #     # preserve GUI state, but want to see where we are
    #     print("KeyboardInterrupt")
    #     raise
    if isinstance(exc, SystemExit):
        # Ctrl-D and warm reboot cause this, not bugs
        raise
    else:
        print("Exception:")
        # show stacktrace for debug photos
        try:
            import uio
            tmp = uio.StringIO()
            sys.print_exception(exc, tmp)
            msg = tmp.getvalue()
            del tmp
            print('===============================================================')
            print(msg)
            print('===============================================================')

            filename = 'error.log'
            saved = save_error_log(msg, filename)

            # Switch immediately to a new card to show the error
            fatal_error_card = {
                'statusbar': {'title': 'FATAL ERROR', 'icon': 'ICON_INFO'},
                'page_micron': microns.PageDot,
                'bg_color': BLACK,
                'flow': PageFlow,
                'args': {'args': {'page_class': LongTextPage, 'text': msg,
                                  'left_micron': None, 'right_micron': None}}
            }

            common.ui.set_cards([fatal_error_card])
            if saved:
                common.ui.set_card_header(title='Saved to microSD', icon='ICON_MICROSD')
            else:
                common.ui.set_card_header(title='Insert microSD', icon='ICON_MICROSD')

            loop = get_event_loop()
            _fatal_card_task = loop.create_task(card_task(fatal_error_card))
            _microsd_task = loop.create_task(save_error_log_to_microsd_task(msg, filename))

        except Exception as exc2:
            sys.print_exception(exc2)


def get_file_list(path=None, include_folders=False, include_parent=False,
                  suffix=None, filter_fn=None, show_hidden=False):
    file_list = []

    with CardSlot() as card:
        if path is None:
            path = card.get_sd_root()

        # Ensure path is build properly
        if not path.startswith(card.get_sd_root()):
            # print('ERROR: The path for get_file_list() must start with "{}"'.format(card.get_sd_root()))
            return []

        # Make sure this path exists and that it is a folder
        if not folder_exists(path):
            # print('ERROR: The path "{}" does not exist'.format(path))
            return []

        files = uos.ilistdir(path)
        for filename, file_type, *var in files:
            # print("filename={} file_type={} var={}  suffix={}".format(filename, file_type, var, suffix))
            # Don't include folders if requested
            is_folder = file_type == 0x4000
            if not include_folders and is_folder:
                continue

            # Skip files with the wrong suffix
            if not is_folder and suffix is not None and not filename.lower().endswith(suffix):
                continue

            # Skip "hidden" files that start with "."
            if filename[0] == '.' and not show_hidden:
                continue

            # Apply file filter, if given (only to files -- folder are included by default)
            if not is_folder and filter_fn is not None and not filter_fn(filename, path):
                continue

            full_path = "{}/{}".format(path, filename)

            file_list.append((filename, full_path, is_folder))

    return file_list


def delete_file(path):
    with CardSlot() as card:
        if path is None:
            return

        # Ensure path is build properly
        if not path.startswith(card.get_sd_root()):
            # print('ERROR: The path for get_file_list() must start with "{}"'.format(card.get_sd_root()))
            return

        if folder_exists(path):
            uos.rmdir(path)

        if file_exists(path):
            uos.remove(path)


class InputMode():
    UPPER_ALPHA = 0
    LOWER_ALPHA = 1
    NUMERIC = 2
    PUNCTUATION = 3

    @ classmethod
    def to_str(cls, mode):
        if mode == InputMode.UPPER_ALPHA:
            return 'A-Z'
        elif mode == InputMode.LOWER_ALPHA:
            return 'a-z'
        elif mode == InputMode.NUMERIC:
            return '0-9'
        elif mode == InputMode.PUNCTUATION:
            return '&$?'
        else:
            return ''

    @ classmethod
    def cycle_to_next(cls, mode):
        if mode == InputMode.NUMERIC:
            return InputMode.LOWER_ALPHA
        elif mode == InputMode.LOWER_ALPHA:
            return InputMode.UPPER_ALPHA
        else:
            return InputMode.NUMERIC

    @ classmethod
    def get_icon(cls, mode):
        if mode == InputMode.UPPER_ALPHA:
            return lv.ICON_INPUT_MODE_UPPER_ALPHA
        elif mode == InputMode.LOWER_ALPHA:
            return lv.ICON_INPUT_MODE_LOWER_ALPHA
        elif mode == InputMode.NUMERIC:
            return lv.ICON_INPUT_MODE_NUMERIC
        elif mode == InputMode.PUNCTUATION:
            return lv.ICON_INPUT_MODE_PUNCTUATION


def B2A(x):
    return str(b2a_hex(x), 'ascii')

# class imported:
#     # Context manager that temporarily imports
#     # a list of modules.
#     # LATER: doubtful this saves any memory when all the code is frozen.
#
#     def __init__(self, *modules):
#         self.modules = modules
#
#     def __enter__(self):
#         # import everything required
#         rv = tuple(__import__(n) for n in self.modules)
#
#         return rv[0] if len(self.modules) == 1 else rv
#
#     def __exit__(self, exc_type, exc_value, traceback):
#
#         for n in self.modules:
#             if n in sys.modules:
#                 del sys.modules[n]
#
#         # recovery that tasty memory.
#         gc.collect()
#
#
# def pretty_delay(n):
#     # decode # of seconds into various ranges, need not be precise.
#     if n < 120:
#         return '%d seconds' % n
#     n /= 60
#     if n < 60:
#         return '%d minutes' % n
#     n /= 60
#     if n < 48:
#         return '%.1f hours' % n
#     n /= 24
#     return 'about %d days' % n
#
#
# def pretty_short_delay(sec):
#     # precise, shorter on screen display
#     if sec >= 3600:
#         return '%2dh %2dm %2ds' % (sec // 3600, (sec//60) % 60, sec % 60)
#     else:
#         return '%2dm %2ds' % ((sec//60) % 60, sec % 60)
#
#
# def pop_count(i):
#     # 32-bit population count for integers
#     # from <https://stackoverflow.com/questions/9829578>
#     i = i - ((i >> 1) & 0x55555555)
#     i = (i & 0x33333333) + ((i >> 2) & 0x33333333)
#
#     return (((i + (i >> 4) & 0xF0F0F0F) * 0x1010101) & 0xffffffff) >> 24


def get_filesize(fn):
    # like os.path.getsize()
    import uos
    return uos.stat(fn)[6]


# def is_dir(fn):
#     from stat import S_ISDIR
#     import uos
#     mode = uos.stat(fn)[0]
#     # print('is_dir() mode={}'.format(mode))
#     return S_ISDIR(mode)


class HexWriter:
    # Emulate a file/stream but convert binary to hex as they write
    def __init__(self, fd):
        self.fd = fd
        self.pos = 0
        self.checksum = trezorcrypto.sha256()

    def __enter__(self):
        self.fd.__enter__()
        return self

    def __exit__(self, *a, **k):
        self.fd.seek(0, 3)          # go to end
        self.fd.write(b'\r\n')
        return self.fd.__exit__(*a, **k)

    def tell(self):
        return self.pos

    def write(self, b):
        self.checksum.update(b)
        self.pos += len(b)

        self.fd.write(b2a_hex(b))

    def seek(self, offset, whence=0):
        assert whence == 0          # limited support
        self.pos = offset
        self.fd.seek((2 * offset), 0)

    def read(self, ll):
        b = self.fd.read(ll * 2)
        if not b:
            return b
        assert len(b) % 2 == 0
        self.pos += len(b) // 2
        return a2b_hex(b)

    def readinto(self, buf):
        b = self.read(len(buf))
        buf[0:len(b)] = b
        return len(b)

    def getvalue(self):
        return self.fd.getvalue()


class Base64Writer:
    # Emulate a file/stream but convert binary to Base64 as they write
    def __init__(self, fd):
        self.fd = fd
        self.runt = b''

    def __enter__(self):
        self.fd.__enter__()
        return self

    def __exit__(self, *a, **k):
        if self.runt:
            self.fd.write(b2a_base64(self.runt))
        self.fd.write(b'\r\n')
        return self.fd.__exit__(*a, **k)

    def write(self, buf):
        if self.runt:
            buf = self.runt + buf
        rl = len(buf) % 3
        self.runt = buf[-rl:] if rl else b''
        if rl < len(buf):
            tmp = b2a_base64(buf[:(-rl if rl else None)])
            # library puts in newlines!?
            assert tmp[-1:] == b'\n', tmp
            assert tmp[-2:-1] != b'=', tmp
            self.fd.write(tmp[:-1])

    def getvalue(self):
        return self.fd.getvalue()


def swab32(n):
    # endian swap: 32 bits
    return ustruct.unpack('>I', ustruct.pack('<I', n))[0]


def xfp2str(xfp):
    # Standardized way to show an xpub's fingerprint... it's a 4-byte string
    # and not really an integer. Used to show as '0x%08x' but that's wrong endian.
    return b2a_hex(ustruct.pack('<I', xfp)).decode().upper()


def str2xfp(txt):
    # Inverse of xfp2str
    return ustruct.unpack('<I', a2b_hex(txt))[0]


# def problem_file_line(exc):
#     # return a string of just the filename.py and line number where
#     # an exception occured. Best used on AssertionError.
#     import uio
#     import sys
#     import ure
#
#     tmp = uio.StringIO()
#     sys.print_exception(exc, tmp)
#     lines = tmp.getvalue().split('\n')[-3:]
#     del tmp
#
#     # convert:
#     #   File "main.py", line 63, in interact
#     #    into just:
#     #   main.py:63
#     #
#     # on simulator, huge path is included, remove that too
#
#     rv = None
#     for ln in lines:
#         mat = ure.match(r'.*"(/.*/|)(.*)", line (.*), ', ln)
#         if mat:
#             try:
#                 rv = mat.group(2) + ':' + mat.group(3)
#             except:
#                 pass
#
#     return rv or str(exc) or 'Exception'


def cleanup_deriv_path(bin_path, allow_star=False):
    # Clean-up path notation as string.
    # - raise exceptions on junk
    # - standardize on 'prime' notation (34' not 34p, or 34h)
    # - assume 'm' prefix, so '34' becomes 'm/34', etc
    # - do not assume /// is m/0/0/0
    # - if allow_star, then final position can be * or *' (wildcard)
    import ure
    from public_constants import MAX_PATH_DEPTH
    try:
        s = str(bin_path, 'ascii').lower()
    except UnicodeError:
        raise AssertionError('must be ascii')

    # empty string is valid
    if s == '':
        return 'm'

    s = s.replace('p', "'").replace('h', "'")
    mat = ure.match(r"(m|m/|)[0-9/']*" + ('' if not allow_star else r"(\*'|\*|)"), s)
    assert mat.group(0) == s, "invalid characters"

    parts = s.split('/')

    # the m/ prefix is optional
    if parts and parts[0] == 'm':
        parts = parts[1:]

    if not parts:
        # rather than: m/
        return 'm'

    assert len(parts) <= MAX_PATH_DEPTH, "too deep"

    for p in parts:
        assert p != '' and p != "'", "empty path component"
        if allow_star and '*' in p:
            # - star or star' can be last only (checked by regex above)
            assert p == '*' or p == "*'", "bad wildcard"
            continue
        if p[-1] == "'":
            p = p[0:-1]
        try:
            ip = int(p, 10)
        except Exception:
            ip = -1
        assert 0 <= ip < 0x80000000 and p == str(ip), "bad component: {}".format(p)

    return 'm/{}'.format('/'.join(parts))


def keypath_to_str(bin_path, prefix='m/', skip=1):
    # take binary path, like from a PSBT and convert into text notation
    rv = prefix + '/'.join(str(i & 0x7fffffff) + ("'" if i & 0x80000000 else "")
                           for i in bin_path[skip:])
    return 'm' if rv == 'm/' else rv


def str_to_keypath(xfp, path):
    # Take a numeric xfp, and string derivation, and make a list of numbers,
    # like occurs in a PSBT.
    # - no error checking here

    rv = [xfp]
    for i in path.split('/'):
        if i == 'm':
            continue
        if not i:
            continue      # trailing or duplicated slashes

        if i[-1] == "'":
            here = int(i[:-1]) | 0x80000000
        else:
            here = int(i)

        rv.append(here)

    return rv


# def match_deriv_path(patterns, path):
#     # check for exact string match, or wildcard match (star in last position)
#     # - both args must be cleaned by cleanup_deriv_path() already
#     # - will accept any path, if 'any' in patterns
#     if 'any' in patterns:
#         return True
#
#     for pat in patterns:
#         if pat == path:
#             return True
#
#         if pat.endswith("/*") or pat.endswith("/*'"):
#             if pat[-1] == "'" and path[-1] != "'":
#                 continue
#             if pat[-1] == "*" and path[-1] == "'":
#                 continue
#
#             # same hardness so check up to last component of path
#             if pat.split('/')[:-1] == path.split('/')[:-1]:
#                 return True
#
#     return False


class DecodeStreamer:
    def __init__(self):
        self.runt = bytearray()

    def more(self, buf):
        # Generator:
        # - accumulate into mod-N groups
        # - strip whitespace
        for ch in buf:
            if chr(ch).isspace():
                continue
            self.runt.append(ch)
            if len(self.runt) == 128 * self.mod:
                yield self.a2b(self.runt)
                self.runt = bytearray()

        here = len(self.runt) - (len(self.runt) % self.mod)
        if here:
            yield self.a2b(self.runt[0:here])
            self.runt = self.runt[here:]


class HexStreamer(DecodeStreamer):
    # be a generator that converts hex digits into binary
    # NOTE: mpy a2b_hex doesn't care about unicode vs bytes
    mod = 2

    def a2b(self, x):
        return a2b_hex(x)


class Base64Streamer(DecodeStreamer):
    # be a generator that converts Base64 into binary
    mod = 4

    def a2b(self, x):
        return a2b_base64(x)


def get_month_str(month):
    if month == 1:
        return "January"
    elif month == 2:
        return "February"
    elif month == 3:
        return "March"
    elif month == 4:
        return "April"
    elif month == 5:
        return "May"
    elif month == 6:
        return "June"
    elif month == 7:
        return "July"
    elif month == 8:
        return "August"
    elif month == 9:
        return "September"
    elif month == 10:
        return "October"
    elif month == 11:
        return "November"
    elif month == 12:
        return "December"


def randint(a, b):
    import struct
    from common import noise

    buf = bytearray(4)
    noise.random_bytes(buf, noise.MCU)
    num = struct.unpack_from(">I", buf)[0]

    result = a + (num % (b - a + 1))
    return result


def bytes_to_hex_str(s):
    return str(b2a_hex(s).upper(), 'ascii')


# # Pass a string pattern like 'foo-{}.txt' and the {} will be replaced by a random 4 bytes hex number
# def random_filename(card, pattern):
#     buf = bytearray(4)
#     common.noise.random_bytes(buf, common.noise.MCU)
#     fn = pattern.format(b2a_hex(buf).decode('utf-8'))
#     return '{}/{}'.format(card.get_sd_root(), fn)
#
#
# def to_json(o):
#     import ujson
#     s = ujson.dumps(o)
#     parts = s.split(', ')
#     lines = ',\n'.join(parts)
#     return lines


def to_str(o):
    s = '{}'.format(o)
    parts = s.split(', ')
    lines = ',\n'.join(parts)
    return lines


def random_hex(num_chars):
    import urandom

    rand = bytearray((num_chars + 1) // 2)
    for i in range(len(rand)):
        rand[i] = urandom.randint(0, 255)
    s = b2a_hex(rand).decode('utf-8').upper()
    return s[:num_chars]


def recolor(color, text):
    # Recolor a fragment of text
    h = '{0:0{1}x}'.format(color, 6)
    return '#{} {}#'.format(h, text)

# def truncate_string_to_width(name, font, max_pixel_width):
#     from common import dis
#     if max_pixel_width <= 0:
#         # print('WARNING: Invalid max_pixel_width passed to truncate_string_to_width(). Must be > 0.')
#         return name
#
#     while True:
#         actual_width = dis.width(name, font)
#         if actual_width < max_pixel_width:
#             return name
#         name = name[0:-1]
#
# # The multisig import code is implemented as a menu, and we are coming from a state machine.
# # We want to be able to show the topmost menu that was pushed onto the stack here and wait for it to exit.
# # This is a hack. Side effect is that the top menu shows briefly after menu exits.
#
#
# async def show_top_menu():
#     from ux import the_ux
#     c = the_ux.top_of_stack()
#     await c.interact()
#
# # TODO: For now this just checks the front bytes, but it could ensure the whole thing is valid


def is_valid_address(address):
    import chains
    chain = chains.current_chain()
    if chain.ctype == 'BTC':
        return (len(address) > 3) and (address[0] == '1' or address[0] == '3' or
                                       (address[0] == 'b' and address[1] == 'c' and address[2] == '1'))
    else:
        return (len(address) > 3) and (address[0] == 'm' or address[0] == 'n' or address[0] == '2' or
                                       (address[0] == 't' and address[1] == 'b' and address[2] == '1'))


# Return array of bytewords where each byte in buf maps to a word
# There are 256 bytewords, so this maps perfectly.
def get_bytewords_for_buf(buf):
    from ur2.bytewords import get_word
    words = []
    for b in buf:
        words.append(get_word(b))

    return words

# # We need an async way for the chooser menu to be shown. This does a local call to interact(), which gives
# # us exactly that. Once the chooser completes, the menu stack returns to the way it was.
#
#
# async def run_chooser(chooser, title, show_checks=True):
#     from ux import the_ux
#     from menu import start_chooser
#     start_chooser(chooser, title=title, show_checks=show_checks)
#     c = the_ux.top_of_stack()
#     await c.interact()
#
# # Return the elements of a list in a random order in a new list
#
#
# def shuffle(list):
#     import urandom
#     new_list = []
#     list_len = len(list)
#     while list_len > 0:
#         i = urandom.randint(0, list_len-1)
#         element = list.pop(i)
#         new_list.append(element)
#         list_len = len(list)
#
#     return new_list


def ensure_folder_exists(path):
    import uos
    try:
        # print('Creating folder: {}'.format(path))
        uos.mkdir(path)
    except Exception as e:
        # print('Folder already exists: {}'.format(e))
        return


def file_exists(path):
    import os
    from stat import S_ISREG

    try:
        s = os.stat(path)
        mode = s[0]
        return S_ISREG(mode)
    except OSError as e:
        return False


def folder_exists(path):
    import os
    from stat import S_ISDIR

    try:
        s = os.stat(path)
        mode = s[0]
        return S_ISDIR(mode)
    except OSError as e:
        return False


def get_accounts():
    from common import settings
    accounts = settings.get('accounts', [])
    accounts.sort(key=lambda a: a.get('acct_num', 0))
    return accounts


def get_accounts_by_xfp(xfp):
    accounts = get_accounts()
    return [acct for acct in accounts if acct.get('xfp', None) == xfp]


def get_account_by_name(name, xfp):
    accounts = get_accounts_by_xfp(xfp)
    for account in accounts:
        if account.get('name') == name:
            return account

    return None


def get_account_by_number(acct_num, xfp):
    accounts = get_accounts_by_xfp(xfp)
    for account in accounts:
        if account.get('acct_num') == acct_num:
            return account

    return None


def get_derived_keys():
    from common import settings
    keys = settings.get('derived_keys', [])
    keys.sort(key=lambda a: (a.get('name', '').lower(), a.get('tn', 0), a.get('index', 0)))
    return keys


def get_derived_key_by_name(name, key_tn, xfp):
    keys = get_derived_keys()
    for key in keys:
        if key['name'] == name and key['tn'] == key_tn and key['xfp'] == xfp:
            return key

    return None


def get_derived_key_by_index(index, key_tn, xfp):
    keys = get_derived_keys()
    for key in keys:
        if key['index'] == index and key['tn'] == key_tn and key['xfp'] == xfp:
            return key

    return None


def get_width_from_num_words(num_words):
    return (num_words - 1) * 11 // 8 + 1


# Only call when there is an active account
# def set_next_addr(new_addr):
#     if not common.active_account:
#         return
#
#     common.active_account.next_addr = new_addr
#
#     accounts = get_accounts()
#     for account in accounts:
#         if account('id') == common.active_account.id:
#             account['next_addr'] = new_addr
#             common.settings.set('accounts', accounts)
#             common.settings.save()
#             break
#
# # Only call when there is an active account
#
#
# def account_exists(name):
#     accounts = get_accounts()
#     for account in accounts:
#         if account.get('name') == name:
#             return True
#
#     return False


def make_next_addr_key(acct_num, addr_type, xfp, chain_type, is_change):
    return '{}.{}.{}/{}{}'.format(chain_type, xfp, acct_num, addr_type, '/1' if is_change else '')


def get_next_addr(acct_num, addr_type, xfp, chain_type, is_change):
    from common import settings
    next_addrs = settings.get('next_addrs', {})
    key = make_next_addr_key(acct_num, addr_type, xfp, chain_type, is_change)
    return next_addrs.get(key, 0)

# Save the next address to use for the specific account and address type


def save_next_addr(acct_num, addr_type, addr_idx, xfp, chain_type, is_change, force_update=False):
    from common import settings
    next_addrs = settings.get('next_addrs', {})
    key = make_next_addr_key(acct_num, addr_type, xfp, chain_type, is_change)

    # Only save the found index if it's newer
    if next_addrs.get(key, -1) < addr_idx or force_update:
        next_addrs[key] = addr_idx
        settings.set('next_addrs', next_addrs)


def get_prev_address_range(range, max_size):
    low, high = range
    size = min(max_size, low)
    return ((low - size, low), size)


def get_next_address_range(range, max_size):
    low, high = range
    return ((high, high + max_size), max_size)


def is_valid_btc_address(address):
    # Strip prefix if present
    if address[0:8].lower() == 'bitcoin:':
        # Find the parameters part and strip it.
        bitcoinparams_start = address.find('?')
        if bitcoinparams_start == -1:
            bitcoinparams_start = len(address)

        address = address[8:bitcoinparams_start]

    # We need to lowercase BECH32 addresses, but not legacy
    # Some wallets format BECH32 in all uppercase, while legacy addresses can have mixed case.
    lower_address = address.lower()
    if lower_address.startswith('bc1') or lower_address.startswith('tb1'):
        address = lower_address

    if not is_valid_address(address):
        return address, False
    else:
        return address, True


def format_btc_address(address, addr_type):
    from public_constants import AF_P2WPKH

    if addr_type == AF_P2WPKH:
        width = 14
    else:
        width = 16

    return split_to_lines(address, width)


def get_backups_folder_path():
    return get_folder_path()


def get_folder_path(folder=DIR_BACKUPS):
    return '{}/{}'.format(CardSlot.get_sd_root(), folder)


def split_to_lines(s, width):
    return '\n'.join([s[i:i + width] for i in range(0, len(s), width)])


def sign_message_digest(digest, subpath):
    # do the signature itself!
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(subpath)
        pk = node.private_key()
        sv.register(pk)

        rv = trezorcrypto.secp256k1.sign(pk, digest)

    return rv


def has_secrets():
    from common import pa
    return not pa.is_secret_blank()


def flatten_list(a_list):
    return [item for sublist in a_list for item in sublist]


def get_basename(file_path):
    return file_path.rsplit('/', 1)[-1]


def split_backup_code(backup_code):
    # Split backup code into groups of 4 digits
    result = []
    for row in range(NUM_BACKUP_CODE_SECTIONS):
        digits = backup_code[row * NUM_DIGITS_PER_BACKUP_CODE_SECTION: (row + 1) * NUM_DIGITS_PER_BACKUP_CODE_SECTION]
        result.append(digits)
    return result


def get_backup_code_as_password(backup_code):
    # Convert array of digits to hyphenated string format like: "1111-2222-3333-4444-5555"
    parts = split_backup_code(backup_code)
    password_parts = []
    for part in parts:
        str_part = ''
        for digit in part:
            str_part = str_part + str(digit)
        password_parts.append(str_part)

    return '-'.join(password_parts)


def get_largest_mem_block(label=''):
    '''Use binary search to make this fast.'''
    import gc

    upper = 512 * 1024
    lower = 0
    size = (upper + lower) // 2

    while True:
        try:
            # print('Try to alloc {} bytes'.format(size))
            buf = bytearray(size)

            # Success!
            buf = None  # Give it back for the next iteration
            gc.collect()

            lower = size
        except Exception:
            upper = size

        size = (upper + lower) // 2
        if upper - lower < 2:
            return lower


def mem_info(label=None, map=False):
    import gc

    largest_block = get_largest_mem_block()
    free = gc.mem_free()
    total = free + gc.mem_alloc()

    print('================================================================================')
    if label is not None:
        print(label)
    print('Available:     {:,} of {:,} bytes'.format(free, total))
    print('Largest Block: {:,} bytes'.format(largest_block))
    if map:
        import machine
        print('\nMachine Info:')
        machine.info(1)
    print('================================================================================')


def set_list(lst, index, value):
    try:
        lst[index] = value
    except IndexError:
        for _ in range(index - len(lst) + 1):
            lst.append(None)
        lst[index] = value


def has_seed():
    from common import pa

    # pa.is_secret_blank() function returns True before we are logged in, which is not right.
    if not is_logged_in():
        return False

    return not pa.is_secret_blank()


def is_logged_in():
    import common
    return common.pa.is_logged_in


def is_dev_build():
    import passport
    return passport.IS_DEV


async def show_page_with_sd_card(page, on_sd_card_change, on_result, on_exception=None):
    """
    Shows a page and polls for user input while polling for SD card insertion/removal at the same time.
    SD card insertion/removal, user input and exception callbacks are available. Returning True from any of
      the callbacks stops the function.

    :param page: a page object to show
    :param on_sd_card_change: a callback on SD card insertion/removal, a single bool parameter indicating
      SD card presence
    :param on_result: a user input callback, a single parameter is the user input.
    :param on_exception: an exception callback, a single parameter is the exception object.
    :return: None
    """
    from files import CardMissingError
    from pages import ErrorPage

    sd_card_change = False
    prev_sd_card_cb = None

    def sd_card_cb():
        nonlocal sd_card_change
        if sd_card_change:
            return

        sd_card_change = True

    def restore_sd_cb():
        nonlocal prev_sd_card_cb
        CardSlot.set_sd_card_change_cb(prev_sd_card_cb)

    # Activate SD card hook
    prev_sd_card_cb = CardSlot.get_sd_card_change_cb()
    CardSlot.set_sd_card_change_cb(sd_card_cb)

    try:
        await page.display()
    except Exception as e:
        print(e)
        page.unmount()
        restore_sd_cb()
        await on_result(None)
        await ErrorPage(text='Unable to display page.').show()
        return

    g = page.poll_for_done()
    while True:
        try:
            next(g)
            await sleep_ms(10)

            # SD card just got inserted or removed
            if sd_card_change:
                sd_card_change = False

                try:
                    with CardSlot():
                        sd_card_present = True
                except CardMissingError:
                    sd_card_present = False

                if on_sd_card_change(sd_card_present):
                    page.restore_statusbar_and_card_header()
                    restore_sd_cb()
                    return

        except StopIteration as result:
            result = result.value

            success = await on_result(result)
            if success:
                page.restore_statusbar_and_card_header()
                restore_sd_cb()
                return

        except Exception as e:
            if on_exception(e):
                page.restore_statusbar_and_card_header()
                restore_sd_cb()
                return


def make_extension_path(ext_name, ext_prop):
    from common import settings
    xfp = xfp2str(settings.get('xfp'))
    return 'ext.{}.{}.{}'.format(ext_name, ext_prop, xfp)


def toggle_extension_enabled(ext_name):
    from common import ui, settings
    ext_path = make_extension_path(ext_name, 'enabled')
    is_enabled = common.settings.get(ext_path, False)
    common.settings.set(ext_path, not is_enabled)
    ui.update_cards_on_top_level()


def is_extension_enabled(ext_name):
    ext_path = make_extension_path(ext_name, 'enabled')
    return common.settings.get(ext_path, False)


def toggle_showing_hidden_keys():
    from common import ui
    showing = common.settings.get('showing_hidden_keys', False)
    common.settings.set_volatile('showing_hidden_keys', not showing)
    ui.update_cards_on_top_level()


def are_hidden_keys_showing():
    showing = common.settings.get('showing_hidden_keys', False)
    return showing


def is_passphrase_active():
    import stash
    return stash.bip39_passphrase != ''


MSG_CHARSET = range(32, 127)
MSG_MAX_SPACES = 4


def validate_sign_text(text, subpath, space_limit=True, check_whitespace=True):
    # Check for leading or trailing whitespace
    if check_whitespace:
        if text[0] == ' ':
            return (subpath, 'File contains leading whitespace.')

        if text[-1] == ' ':
            return (subpath, 'File contains trailing whitespace.')

    # Ensure characters are in range and not too many spaces
    run = 0
    # print('text="{}"'.format(text))
    for ch in text:
        # print('ch="{}"'.format(ch))
        if ord(ch) not in MSG_CHARSET:
            return (subpath, 'File contains non-ASCII character: 0x%02x' % ord(ch))

        if space_limit:
            if ch == ' ':
                run += 1
                if run >= MSG_MAX_SPACES:
                    return (subpath, 'File contains more than {} spaces in a row'.format(MSG_MAX_SPACES - 1))
            else:
                run = 0

    # Check subpath, if given
    if subpath:
        try:
            assert subpath[0:1] == 'm'
            subpath = cleanup_deriv_path(subpath)
        except BaseException:
            return (subpath, 'Second line, if included, must specify a subkey path.')

    return (subpath, None)


def get_screen_brightness(default_value):
    if passport.IS_COLOR:
        return common.system.get_screen_brightness(default_value)
    else:
        return common.settings.get('screen_brightness', default_value)


def set_screen_brightness(value):
    if passport.IS_COLOR:
        common.system.set_screen_brightness(value)
    else:
        common.settings.set('screen_brightness', value)


async def clear_psbt_flash(psbt_len):
    from utils import spinner_task
    from tasks import clear_psbt_from_external_flash_task

    await spinner_task(None, clear_psbt_from_external_flash_task, args=[psbt_len])


def get_words_from_seed(seed):
    try:
        words = trezorcrypto.bip39.from_data(seed).split(' ')
        return (words, None)
    except Exception as e:
        return (None, '{}'.format(e))


def nostr_pubkey_from_pk(pk):
    from trezorcrypto import secp256k1
    return secp256k1.publickey(pk, True)[1:]


def nostr_nip19_from_key(key, key_type):  # generate nsec/npub
    import tcc
    return tcc.codecs.bech32_plain_encode(key_type, key)


def nostr_sign(key, message):
    from foundation import secp256k1
    return secp256k1.schnorr_sign(message, key)


months = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'Aug',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December',
}


def timestamp_to_str(time):
    import utime

    time_tup = utime.gmtime(time)
    return "{} {}, {}\n{}:{:02d}".format(months[time_tup[1]],  # Month
                                         time_tup[2],          # Day
                                         time_tup[0],          # Year
                                         time_tup[3],          # Hour
                                         time_tup[4],          # Minute
                                         )


# This is a flow function, so it needs to be async
async def show_card_missing(flow):
    from pages import InsertMicroSDPage

    # This makes the return type consistent with the caller
    if hasattr(flow, "return_bool") and flow.return_bool:
        result = False
    else:
        result = None

    if hasattr(flow, "automatic") and flow.automatic:
        flow.set_result(result)
        return

    retry = await InsertMicroSDPage().show()
    if retry:
        flow.back()
    else:
        flow.set_result(result)


# This assumes the function passed in is async
def bind(instance, func, as_name=None):
    if as_name is None:
        as_name = func.__name__

    async def method(*args, **kwargs):
        return await func(instance, *args, **kwargs)

    setattr(instance, as_name, method)
    return method


def derive_icon(icon):
    if isinstance(icon, str):
        return getattr(lv, icon)
    return icon


def toggle_key_hidden(item, key):
    from common import settings
    from utils import get_derived_keys

    keys = get_derived_keys()
    keys.remove(key)
    key['hidden'] = not key['hidden']
    keys.append(key)
    settings.set('derived_keys', keys)


def is_key_hidden(key):
    from utils import get_derived_key_by_index

    updated = get_derived_key_by_index(key['index'], key['tn'], key['xfp'])
    return updated['hidden']


def escape_text(text):
    return text.replace("#", "##")


def stylize_address(address):
    from styles.colors import TEXT_GREY_HEX, BLACK_HEX

    stylized = ''
    colors = [BLACK_HEX, TEXT_GREY_HEX]
    color_index = 0
    block = ''

    for i in range(len(address)):
        # Every 4 characters, append the recolored block of characters
        if i % 4 == 0 and i != 0:
            stylized += recolor(colors[color_index], block)
            block = ''
            color_index ^= 1
            # Every 4 blocks, start a new line
            if i % 16 == 0:
                stylized += '\n'
            else:
                stylized += ' '
        block += address[i]
    stylized += recolor(colors[color_index], block)

    return stylized


def get_single_address(xfp,
                       chain,
                       index,
                       is_multisig,
                       multisig_wallet,
                       is_change,
                       deriv_path,
                       addr_type):
    import stash

    change_bit = 1 if is_change else 0
    with stash.SensitiveValues() as sv:
        if is_multisig:
            (curr_idx, paths, address, script) = list(multisig_wallet.yield_addresses(
                start_idx=index,
                count=1,
                change_idx=change_bit))[0]
        else:
            addr_path = '{}/{}/{}'.format(deriv_path, change_bit, index)
            node = sv.derive_path(addr_path)
            address = sv.chain.address(node, addr_type)

    return address


# EOF
