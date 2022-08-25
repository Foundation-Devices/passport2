# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# multisig_wallet.py - MultisigWallet class (data only -- no UI code)


import stash
import chains
from styles.colors import COPPER_HEX, FD_BLUE_HEX
import ustruct
import ure
import tcc
from ubinascii import hexlify as b2a_hex
from utils import xfp2str, str2xfp, cleanup_deriv_path, keypath_to_str, str_to_keypath
from public_constants import (AF_P2SH, AF_P2WSH_P2SH, AF_P2WSH, AFC_SCRIPT,
                              TRUST_OFFER, TRUST_PSBT, TRUST_VERIFY, MAX_SIGNERS)
from constants import MAX_MULTISIG_NAME_LEN
from exceptions import FatalPSBTIssue
from opcodes import OP_CHECKMULTISIG
import trezorcrypto


def disassemble_multisig_mn(redeem_script):
    # pull out just M and N from script. Simple, faster, no memory.

    assert MAX_SIGNERS == 15
    assert redeem_script[-1] == OP_CHECKMULTISIG, 'need CHECKMULTISIG'

    M = redeem_script[0] - 80
    N = redeem_script[-2] - 80

    return M, N


def disassemble_multisig(redeem_script):
    # Take apart a standard multisig's redeem/witness script, and return M/N and public keys
    # - only for multisig scripts, not general purpose
    # - expect OP_1 (pk1) (pk2) (pk3) OP_3 OP_CHECKMULTISIG for 1 of 3 case
    # - returns M, N, (list of pubkeys)
    # - for very unlikely/impossible asserts, dont document reason; otherwise do.
    from serializations import disassemble

    M, N = disassemble_multisig_mn(redeem_script)
    assert 1 <= M <= N <= MAX_SIGNERS, 'M/N range'
    assert len(redeem_script) == 1 + (N * 34) + 1 + 1, 'bad len'

    # generator function
    dis = disassemble(redeem_script)

    # expect M value first
    ex_M, opcode = next(dis)
    assert ex_M == M and opcode is None, 'bad M'

    # need N pubkeys
    pubkeys = []
    for idx in range(N):
        data, opcode = next(dis)
        assert opcode is None and len(data) == 33, 'data'
        assert data[0] == 0x02 or data[0] == 0x03, 'Y val'
        pubkeys.append(data)

    assert len(pubkeys) == N

    # next is N value
    ex_N, opcode = next(dis)
    assert ex_N == N and opcode is None

    # finally, the opcode: CHECKMULTISIG
    data, opcode = next(dis)
    assert opcode == OP_CHECKMULTISIG

    # must have reached end of script at this point
    try:
        next(dis)
        raise AssertionError("too long")
    except StopIteration:
        # expected, since we're reading past end
        pass

    return M, N, pubkeys


def make_redeem_script(M, nodes, subkey_idx):
    # take a list of BIP32 nodes, and derive Nth subkey (subkey_idx) and make
    # a standard M-of-N redeem script for that. Always applies BIP67 sorting.
    N = len(nodes)
    assert 1 <= M <= N <= MAX_SIGNERS

    pubkeys = []
    for n in nodes:
        copy = n.clone()
        copy.derive(subkey_idx, True)
        # 0x21 = 33 = len(pubkey) = OP_PUSHDATA(33)
        pubkeys.append(b'\x21' + copy.public_key())

    pubkeys.sort()

    # serialize redeem script
    pubkeys.insert(0, bytes([80 + M]))
    pubkeys.append(bytes([80 + N, OP_CHECKMULTISIG]))

    return b''.join(pubkeys)


class MultisigWallet:
    # Capture the info we need to store long-term in order to participate in a
    # multisig wallet as a co-signer.
    # - can be saved to nvram
    # - can be imported from a simple text file
    # - can be displayed to user in a menu (and deleted)
    # - required during signing to verify change outputs
    # - can reconstruct any redeem script from this
    # Challenges:
    # - can be big, taking big % of 4k storage in nvram
    # - complex object, want to have flexibility going forward
    FORMAT_NAMES = [
        (AF_P2SH, 'p2sh'),
        (AF_P2WSH, 'p2wsh'),
        (AF_P2WSH_P2SH, 'p2sh-p2wsh'),  # new name
        (AF_P2WSH_P2SH, 'p2wsh-p2sh'),  # old name
    ]

    def __init__(self, name, m_of_n, xpubs, id, addr_fmt=AF_P2SH, chain_type='BTC', deriv=None):
        self.storage_idx = -1

        self.name = name[:MAX_MULTISIG_NAME_LEN]
        assert len(m_of_n) == 2
        self.M, self.N = m_of_n
        self.chain_type = chain_type or 'BTC'
        assert len(xpubs[0]) == 3
        self.xpubs = xpubs                  # list of (xfp(int), deriv, xpub(str))
        self.id = id                        # Unique id to associate multisig info with an account
        self.addr_fmt = addr_fmt            # address format for wallet
        self.my_deriv = deriv

        # calc useful cache value: numeric xfp+subpath, with lookup
        self.xfp_paths = {}
        for xfp, deriv, _ in self.xpubs:
            self.xfp_paths[xfp] = str_to_keypath(xfp, deriv)

        assert len(self.xfp_paths) == self.N, 'dup XFP'         # not supported

    @classmethod
    def render_addr_fmt(cls, addr_fmt):
        for k, v in cls.FORMAT_NAMES:
            if k == addr_fmt:
                return v.upper()
        return '?'

    @property
    def chain(self):
        return chains.get_chain(self.chain_type)

    @classmethod
    def get_trust_policy(cls):
        from common import settings

        which = settings.get('multisig_policy', None)

        if which is None:
            which = TRUST_VERIFY if cls.exists() else TRUST_OFFER

        return which

    def serialize(self):
        # return a JSON-able object
        from common import noise

        opts = dict()
        if self.addr_fmt != AF_P2SH:
            opts['ft'] = self.addr_fmt
        if self.chain_type != 'BTC':
            opts['ch'] = self.chain_type

        # Data compression: most legs will all use same derivation.
        # put a int(0) in place and set option 'pp' to be derivation
        # (used to be common_prefix assumption)
        pp = list(sorted(set(d for _, d, _ in self.xpubs)))
        if len(pp) == 1:
            # generate old-format data, to preserve firmware downgrade path
            xp = [(a, c) for a, deriv, c in self.xpubs]
            opts['pp'] = pp[0]
        else:
            # allow for distinct deriv paths on each leg
            opts['d'] = pp
            xp = [(a, pp.index(deriv), c) for a, deriv, c in self.xpubs]

        return (self.name, (self.M, self.N), xp, opts, self.id, self.my_deriv)

    @classmethod
    def deserialize(cls, vals, idx=-1):
        # take json object, make instance.
        name, m_of_n, xpubs, opts, id, deriv = vals

        # TODO: This looks like CC legacy code - we can probably remove
        if len(xpubs[0]) == 2:
            # promote from old format to new: assume common prefix is the derivation
            # for all of them
            # PROBLEM: we don't have enough info if no common prefix can be assumed
            common_prefix = opts.get('pp', None)
            if not common_prefix:
                # TODO: this should raise a warning, not supported anymore
                common_prefix = 'm'
            xpubs = [(a, common_prefix, b) for a, b in xpubs]
        else:
            # new format decompression
            if 'd' in opts:
                derivs = opts.get('d', None)
                xpubs = [(a, derivs[b], c) for a, b, c in xpubs]

        rv = cls(name, m_of_n, xpubs, id, addr_fmt=opts.get('ft', AF_P2SH),
                 chain_type=opts.get('ch', 'BTC'), deriv=deriv)
        rv.storage_idx = idx

        return rv

    @classmethod
    def iter_wallets(cls, M=None, N=None, not_idx=None, addr_fmt=None):
        # yield MS wallets we know about, that match at least right M,N if known.
        # - this is only place we should be searching this list, please!!
        from common import settings
        lst = settings.get('multisig', [])

        for idx, rec in enumerate(lst):
            if idx == not_idx:
                # ignore one by index
                continue

            if M or N:
                # peek at M/N
                has_m, has_n = tuple(rec[1])
                if M is not None and has_m != M:
                    continue
                if N is not None and has_n != N:
                    continue

            if addr_fmt is not None:
                opts = rec[3]
                af = opts.get('ft', AF_P2SH)
                if af != addr_fmt:
                    continue

            yield cls.deserialize(rec, idx)

    def get_xfp_paths(self):
        # return list of lists [xfp, *deriv]
        return list(self.xfp_paths.values())

    @classmethod
    def find_match(cls, M, N, xfp_paths, addr_fmt=None):
        # Find index of matching wallet
        # - xfp_paths is list of lists: [xfp, *path] like in psbt files
        # - M and N must be known
        # - returns instance, or None if not found
        for rv in cls.iter_wallets(M, N, addr_fmt=addr_fmt):
            if rv.matching_subpaths(xfp_paths):
                return rv

        return None

    @classmethod
    def find_candidates(cls, xfp_paths, addr_fmt=None, M=None):
        # Return a list of matching wallets for various M values.
        # - xpfs_paths hsould already be sorted
        # - returns set of matches, of any M value

        # we know N, but not M at this point.
        N = len(xfp_paths)

        matches = []
        for rv in cls.iter_wallets(M=M, addr_fmt=addr_fmt):
            if rv.matching_subpaths(xfp_paths):
                matches.append(rv)

        return matches

    def matching_subpaths(self, xfp_paths):
        # Does this wallet use same set of xfp values, and
        # the same prefix path per-each xfp, as indicated
        # xfp_paths (unordered)?
        # - could also check non-prefix part is all non-hardened
        for x in xfp_paths:
            if x[0] not in self.xfp_paths:
                return False
            prefix = self.xfp_paths[x[0]]

            if len(x) < len(prefix):
                # PSBT specs a path shorter than wallet's xpub
                # print('path len: %d vs %d' % (len(prefix), len(x)))
                return False

            comm = len(prefix)
            if tuple(prefix[:comm]) != tuple(x[:comm]):
                # xfp => maps to wrong path
                # print('path mismatch:\n%r\n%r\ncomm=%d' % (prefix[:comm], x[:comm], comm))
                return False

        return True

    def assert_matching(self, M, N, xfp_paths):
        # compare in-memory wallet with details recovered from PSBT
        # - xfp_paths must be sorted already
        assert (self.M, self.N) == (M, N), "M/N mismatch"
        assert len(xfp_paths) == N, "XFP count"
        assert self.matching_subpaths(xfp_paths), "wrong XFP/derivs"

    @classmethod
    def quick_check(cls, M, N, xfp_xor):
        # quicker? USB method.
        rv = []
        for ms in cls.iter_wallets(M, N):
            x = 0
            for xfp in ms.xfp_paths.keys():
                x ^= xfp
            if x != xfp_xor:
                continue

            return True

        return False

    @classmethod
    def get_all(cls):
        # return them all, as a generator
        return cls.iter_wallets()

    @classmethod
    def exists(cls):
        # are there any wallets defined?
        from common import settings
        return bool(settings.get('multisig', False))

    @classmethod
    def get_count(cls):
        from common import settings
        lst = settings.get('multisig', [])
        return len(lst)

    @classmethod
    def get_by_idx(cls, nth):
        # instance from index number (used in menu)
        from common import settings
        lst = settings.get('multisig', [])
        try:
            obj = lst[nth]
        except IndexError:
            return None

        return cls.deserialize(obj, nth)

    @classmethod
    def get_by_id(cls, id):
        # instance from unique id
        from common import settings

        lst = settings.get('multisig', [])
        # print('get_by_id(): settings.multisig={}'.format(lst))

        for idx, v in enumerate(lst):
            if v[4] == id:
                return cls.deserialize(v, idx)

        return None

    @classmethod
    def delete_by_id(cls, id):
        from utils import to_str
        from common import settings

        lst = settings.get('multisig', [])
        # print('delete_by_id(): BEFORE: settings.multisig={}'.format(to_str(lst)))

        for idx, v in enumerate(lst):
            if v[4] == id:
                del lst[idx]
                # print('delete_by_id(): AFTER:  settings.multisig={}'.format(to_str(lst)))
                settings.set('multisig', lst)
                # Assumes caller will call save if it's important to do immediately
                # We do this as part of updating 'accounts' too, so we only want one save call.

    def has_similar(self):
        # check if we already have a saved duplicate to this proposed wallet
        # - return (name_change, diff_items, count_similar) where:
        #   - name_change is existing wallet that has exact match, different name
        #   - diff_items: text list of similarity/differences
        #   - count_similar: same N, same xfp+paths

        lst = self.get_xfp_paths()
        c = self.find_match(self.M, self.N, lst, addr_fmt=self.addr_fmt)
        if c:
            # All details are same: M/N, paths, addr fmt
            if self.xpubs != c.xpubs:
                return None, ['xpubs'], 0
            elif self.name == c.name:
                return None, [], 1
            else:
                return c, ['name'], 0

        similar = MultisigWallet.find_candidates(lst)
        if not similar:
            # no matches, good.
            return None, [], 0

        # See if the xpubs are changing, which is risky... other differences like
        # name are okay.
        diffs = set()
        name_diff = None
        for c in similar:
            if c.M != self.M:
                diffs.add('M differs')
            if c.addr_fmt != self.addr_fmt:
                diffs.add('address type')
            if c.name != self.name:
                diffs.add('name')
            if c.xpubs != self.xpubs:
                diffs.add('xpubs')

        return None, diffs, len(similar)

    def xpubs_with_xfp(self, xfp):
        # return set of indexes of xpubs with indicated xfp
        return set(xp_idx for xp_idx, (wxfp, _, _) in enumerate(self.xpubs)
                   if wxfp == xfp)

    def yield_addresses(self, start_idx, count, change_idx=0):
        # Assuming a suffix of /0/0 on the defined prefix's, yield
        # possible deposit addresses for this wallet. Never show
        # user the resulting addresses because we cannot be certain
        # they are valid and could be signed. And yet, dont blank too many
        # spots or else an attacker could grid out a suitable replacement.
        ch = self.chain

        assert self.addr_fmt, 'no addr fmt known'

        # setup
        nodes = []
        paths = []
        for xfp, deriv, xpub in self.xpubs:
            # print('xfp={}'.format(xfp))
            # print('deriv={}'.format(deriv))
            # print('xpub={}'.format(xpub))
            # load bip32 node for each cosigner, derive /0/ based on change idx
            node = ch.deserialize_node(xpub, AF_P2SH)
            node.derive(change_idx, True)
            nodes.append(node)

            # indicate path used (for UX)
            path = "(m=%s)/%s/%d/{idx}" % (xfp2str(xfp), deriv, change_idx)
            paths.append(path)

        idx = start_idx
        while count:
            # make the redeem script, convert into address
            script = make_redeem_script(self.M, nodes, idx)  # idx is the address index
            addr = ch.p2sh_address(self.addr_fmt, script)
            # addr = addr[0:12] + '___' + addr[12+3:]

            yield idx, [p.format(idx=idx) for p in paths], addr, script

            idx += 1
            count -= 1

    def validate_script(self, redeem_script, subpaths=None, xfp_paths=None):
        # Check we can generate all pubkeys in the redeem script, raise on errors.
        # - working from pubkeys in the script, because duplicate XFP can happen
        #
        # redeem_script: what we expect and we were given
        # subpaths: pubkey => (xfp, *path)
        # xfp_paths: (xfp, *path) in same order as pubkeys in redeem script

        subpath_help = []
        used = set()
        ch = self.chain

        M, N, pubkeys = disassemble_multisig(redeem_script)
        assert M == self.M and N == self.N, 'wrong M/N in script'

        for pk_order, pubkey in enumerate(pubkeys):
            check_these = []

            if subpaths:
                # in PSBT, we are given a map from pubkey to xfp/path, use it
                # while remembering it's potentially one-2-many
                # TODO: this could be simpler now
                assert pubkey in subpaths, "unexpected pubkey"
                xfp, *path = subpaths[pubkey]

                for xp_idx, (wxfp, _, xpub) in enumerate(self.xpubs):
                    if wxfp != xfp:
                        continue
                    if xp_idx in used:
                        continue      # only allow once
                    check_these.append((xp_idx, path))
            else:
                # Without PSBT, USB caller must provide xfp+path
                # in same order as they occur inside redeem script.
                # Working solely from the redeem script's pubkeys, we
                # wouldn't know which xpub to use, nor correct path for it.
                xfp, *path = xfp_paths[pk_order]

                for xp_idx in self.xpubs_with_xfp(xfp):
                    if xp_idx in used:
                        continue      # only allow once
                    check_these.append((xp_idx, path))

            here = None
            too_shallow = False
            for xp_idx, path in check_these:
                # matched fingerprint, try to make pubkey that needs to match
                # print('xpubs={}'.format(self.xpubs))
                xpub = self.xpubs[xp_idx][-1]

                node = ch.deserialize_node(xpub, AF_P2SH)
                assert node
                dp = node.depth()

                # print("%s => deriv=%s dp=%d len(path)=%d path=%s" %
                #        (xfp2str(xfp), self.xpubs[xp_idx][1], dp, len(path), path))

                if not (0 <= dp <= len(path)):
                    # obscure case: xpub isn't deep enough to represent
                    # indicated path... not wrong really.
                    too_shallow = True
                    continue

                for sp in path[dp:]:
                    assert not (sp & 0x80000000), 'hard deriv'
                    node.derive(sp, True)     # works in-place

                found_pk = node.public_key()

                # Document path(s) used. Not sure this is useful info to user tho.
                # - Do not show what we can't verify: we don't really know the hardeneded
                #   part of the path from fingerprint to here.
                here = '(m=%s)\n' % xfp2str(xfp)
                if dp != len(path):
                    here += 'm' + ('/_' * dp) + keypath_to_str(path[dp:], '/', 0)

                if found_pk != pubkey:
                    # Not a match but not an error by itself, since might be
                    # another dup xfp to look at still.

                    # print('pk mismatch: %s => %s != %s' % (
                    #                here, b2a_hex(found_pk), b2a_hex(pubkey)))
                    continue

                subpath_help.append(here)

                used.add(xp_idx)
                break
            else:
                msg = 'pk#%d wrong' % (pk_order + 1)
                if not check_these:
                    msg += ', unknown XFP'
                elif here:
                    msg += ', tried: ' + here
                if too_shallow:
                    msg += ', too shallow'
                raise AssertionError(msg)

            if pk_order:
                # verify sorted order
                assert bytes(pubkey) > bytes(pubkeys[pk_order - 1]), 'BIP67 violation'

        assert len(used) == self.N, 'not all keys used: %d of %d' % (len(used), self.N)

        return subpath_help

    @classmethod
    def from_file(cls, config, name=None):
        # Given a simple text file, parse contents and create instance (unsaved).
        # format is:         label: value
        # where label is:
        #       name: nameforwallet
        #       policy: M of N
        #       format: p2sh  (+etc)
        #       derivation: m/45'/0     (common prefix)
        #       (8digithex): xpub of cosigner
        #
        # quick checks:
        # - name: 1-20 ascii chars
        # - M of N line (assume N of N if not spec'd)
        # - xpub: any bip32 serialization we understand, but be consistent
        #
        from common import settings

        my_xfp = settings.get('xfp')
        deriv = None
        xpubs = []
        M, N = -1, -1
        has_mine = 0
        addr_fmt = AF_P2SH
        my_deriv = None
        expect_chain = chains.current_chain().ctype

        if isinstance(config, (bytes, bytearray)):
            config = config.decode('utf-8')

        lines = config.split('\n')

        for ln in lines:
            # remove comments
            comm = ln.find('#')
            if comm == 0:
                if ':' in ln:   # Could be a derivation path in a comment
                    # Strip off the comment and let the line get trimmed/parsed below
                    ln = ln[1:]
                else:
                    continue
            elif comm != -1:
                if not ln[comm + 1:comm + 2].isdigit():
                    ln = ln[0:comm]

            ln = ln.strip()

            if ':' not in ln:
                if 'pub' in ln:
                    # pointless optimization: allow bare xpub if we can calc xfp
                    label = '0' * 8
                    value = ln
                else:
                    # complain?
                    # if ln: print("no colon: " + ln)
                    continue
            else:
                label, value = ln.split(':', 1)
                label = label.lower()

            value = value.strip()

            if label == 'name':
                name = value
            elif label == 'policy':
                try:
                    # accepts: 2 of 3    2/3    2,3    2 3   etc
                    mat = ure.search(r'(\d+)\D*(\d+)', value)
                    assert mat
                    M = int(mat.group(1))
                    N = int(mat.group(2))
                    assert 1 <= M <= N <= MAX_SIGNERS
                except BaseException:
                    raise AssertionError('bad policy line')

            elif label == 'derivation':
                # reveal the path derivation for following key(s)
                try:
                    assert value, 'blank'
                    deriv = cleanup_deriv_path(value)
                except BaseException as exc:
                    raise AssertionError('bad derivation line: ' + str(exc))

            elif label == 'format':
                # pick segwit vs. classic vs. wrapped version
                value = value.lower()
                for fmt_code, fmt_label in cls.FORMAT_NAMES:
                    if value == fmt_label:
                        addr_fmt = fmt_code
                        break
                else:
                    raise AssertionError('bad format line')
            elif len(label) == 8:
                try:
                    xfp = str2xfp(label)
                except BaseException:
                    # complain?
                    # print("Bad xfp: " + ln)
                    continue

                # deserialize, update list and lots of checks
                is_mine = cls.check_xpub(xfp, value, deriv, expect_chain, my_xfp, xpubs)
                if is_mine:
                    # HACK: We need to know which deriv path is for our XPUB when creating a new account
                    #       This is ugly, but avoids
                    my_deriv = deriv  # Use the last-parsed (pattern is Derivation, then XFP: XPUB
                    has_mine += 1

        assert len(xpubs), 'No XPUBS found.'

        if M == N == -1:
            # default policy: all keys
            N = M = len(xpubs)

        if not name:
            # provide a default name
            name = '%d-of-%d' % (M, N)

        try:
            name = str(name, 'ascii')
            name = name[:MAX_MULTISIG_NAME_LEN]
        except BaseException:
            raise AssertionError('Name must be ASCII, and 1 to 20 characters long.')

        assert 1 <= M <= N <= MAX_SIGNERS, 'M/N range'
        assert N == len(xpubs), 'wrong # of xpubs, expect %d' % N
        assert addr_fmt & AFC_SCRIPT, 'script style addr fmt'

        # check we're included... do not insert ourselves, even tho we
        # have enough info, simply because other signers need to know my xpubkey anyway
        assert has_mine != 0, 'File does not include a key owned by this Passport'
        assert has_mine == 1    # 'my key included more than once'

        from common import noise
        # Hacky way to give the wallet a unique ID and pass it back to the New Account flow for correlation
        unique_id = bytearray(8)
        noise.random_bytes(unique_id, noise.MCU)
        unique_id = b2a_hex(unique_id).decode('utf-8')

        # done. have all the parts
        return cls(name, (M, N), xpubs, unique_id, addr_fmt=addr_fmt, chain_type=expect_chain, deriv=my_deriv)

    @classmethod
    def check_xpub(cls, xfp, xpub, deriv, expect_chain, my_xfp, xpubs):
        # Shared code: consider an xpub for inclusion into a wallet, if ok, append
        # to list: xpubs with a tuple: (xfp, deriv, xpub)
        # return T if it's our own key
        # - deriv can be None, and in very limited cases can recover derivation path
        # - could enforce all same depth, and/or all depth >= 1, but
        #   seems like more restrictive than needed, so "m" is allowed

        try:
            # Note: addr fmt detected here via SLIP-132 isn't useful
            node, chain, _ = import_xpub(xpub)
        except BaseException:
            raise AssertionError('unable to parse xpub')

        # print('node={}'.format(node))
        # print('node.private_key()={}'.format(node.private_key()))
        # print('xfp={}'.format(xfp))
        # print('xpub={}'.format(xpub))
        # print('expect_chain={}'.format(expect_chain))
        # print('my_xfp={}'.format(my_xfp))
        # print('xpubs={}'.format(xpubs))

        # assert node.private_key() == None       # 'no privkeys plz'
        assert chain.ctype == expect_chain      # 'wrong chain'

        depth = node.depth()

        if depth == 1:
            if not xfp:
                # allow a shortcut: zero/omit xfp => use observed parent value
                xfp = node.fingerprint()
            else:
                # generally cannot check fingerprint values, but if we can, do so.
                assert node.fingerprint() == xfp, 'xfp depth=1 wrong'

        assert xfp, 'need fingerprint'          # happens if bare xpub given

        # In most cases, we cannot verify the derivation path because it's hardened
        # and we know none of the private keys involved.
        if depth == 1:
            # but derivation is implied at depth==1
            guess = keypath_to_str([node.child_num()], skip=0)

            if deriv:
                assert guess == deriv, '%s != %s' % (guess, deriv)
            else:
                deriv = guess           # reachable? doubt it

        assert deriv, 'empty deriv'         # or force to be 'm'?
        assert deriv[0] == 'm'

        # path length of derivation given needs to match xpub's depth
        p_len = deriv.count('/')
        assert p_len == depth, 'deriv %d != %d xpub depth (xfp=%s)' % (
            p_len, depth, xfp2str(xfp))

        if xfp == my_xfp:
            # its supposed to be my key, so I should be able to generate pubkey
            # - might indicate collision on xfp value between co-signers,
            #   and that's not supported
            with stash.SensitiveValues() as sv:
                chk_node = sv.derive_path(deriv)
                assert node.public_key() == chk_node.public_key(), \
                    "(m=%s)/%s wrong pubkey" % (xfp2str(xfp), deriv[2:])

        # serialize xpub w/ BIP32 standard now.
        # - this has effect of stripping SLIP-132 confusion away
        xpubs.append((xfp, deriv, chain.serialize_public(node, AF_P2SH)))

        return (xfp == my_xfp)

    def make_fname(self, prefix, suffix='txt'):
        rv = '%s-%s.%s' % (prefix, self.name, suffix)
        return rv.replace(' ', '_')

    # def render_export(self, fp):
    #     # print("Name: %s\nPolicy: %d of %d" % (self.name, self.M, self.N), file=fp)

    #     if self.addr_fmt != AF_P2SH:
    #         print("Format: " + self.render_addr_fmt(self.addr_fmt), file=fp)

    #     last_deriv = None
    #     for xfp, deriv, val in self.xpubs:
    #         if last_deriv != deriv:
    #             print("\nDerivation: %s\n" % deriv, file=fp)
    #             last_deriv = deriv

    #         print('%s: %s' % (xfp2str(xfp), val), file=fp)

    @classmethod
    def guess_addr_fmt(cls, npath):
        # Assuming  the bips are being respected, what address format will be used,
        # based on indicated numeric subkey path observed.
        # - return None if unsure, no errors
        #
        # ( "m/45'", 'p2sh', AF_P2SH),
        # ( "m/48'/{coin}'/0'/1'", 'p2sh_p2wsh', AF_P2WSH_P2SH),
        # ( "m/48'/{coin}'/0'/2'", 'p2wsh', AF_P2WSH)

        top = npath[0] & 0x7fffffff
        if top == npath[0]:
            # non-hardened top? rare/bad
            return

        if top == 45:
            return AF_P2SH

        if top == 48:
            if len(npath) < 4:
                return

            last = npath[3] & 0x7fffffff
            if last == 1:
                return AF_P2WSH_P2SH
            if last == 2:
                return AF_P2WSH

    @classmethod
    def import_from_psbt(cls, M, N, xpubs_list):
        # given the raw data fro PSBT global header, offer the user
        # the details, and/or bypass that all and just trust the data.
        # - xpubs_list is a list of (xfp+path, binary BIP32 xpub)
        # - already know not in our records.
        from common import settings

        trust_mode = cls.get_trust_policy()
        # print('import_from_psbt(): trust_mode = {}'.format(trust_mode))

        if trust_mode == TRUST_VERIFY:
            # already checked for existing import and wasn't found, so fail
            raise FatalPSBTIssue("XPUBs in PSBT do not match any existing wallet")

        # build up an in-memory version of the wallet.
        #  - capture address format based on path used for my leg (if standards compliant)

        assert N == len(xpubs_list)
        assert 1 <= M <= N <= MAX_SIGNERS, 'M/N range'
        my_xfp = settings.get('xfp')

        expect_chain = chains.current_chain().ctype
        xpubs = []
        has_mine = 0

        for k, v in xpubs_list:
            xfp, *path = ustruct.unpack_from('<%dI' % (len(k) // 4), k, 0)
            xpub = tcc.codecs.b58_encode(v)
            is_mine = cls.check_xpub(xfp, xpub, keypath_to_str(path, skip=0),
                                     expect_chain, my_xfp, xpubs)
            if is_mine:
                has_mine += 1
                addr_fmt = cls.guess_addr_fmt(path)

        assert has_mine == 1         # 'my key not included'

        name = 'PSBT-%d-of-%d' % (M, N)
        ms = cls(name, (M, N), xpubs, -1, chain_type=expect_chain, addr_fmt=addr_fmt or AF_P2SH)

        # may just keep just in-memory version, no approval required, if we are
        # trusting PSBT's today, otherwise caller will need to handle UX w.r.t new wallet
        return ms, (trust_mode != TRUST_PSBT)

    def validate_psbt_xpubs(self, xpubs_list):
        # The xpubs provided in PSBT must be exactly right, compared to our record.
        # But we're going to use our own values from setup time anyway.
        # Check:
        # - chain codes match what we have stored already
        # - pubkey vs. path will be checked later
        # - xfp+path already checked when selecting this wallet
        # - some cases we cannot check, so count those for a warning
        # Any issue here is a fraud attempt in some way, not innocent.
        # But it would not have tricked us and so the attack targets some other signer.
        assert len(xpubs_list) == self.N

        for k, v in xpubs_list:
            xfp, *path = ustruct.unpack_from('<%dI' % (len(k) // 4), k, 0)
            xpub = tcc.codecs.b58_encode(v)

            # cleanup and normalize xpub
            tmp = []
            self.check_xpub(xfp, xpub, keypath_to_str(path, skip=0), self.chain_type, 0, tmp)
            (_, deriv, xpub_reserialized) = tmp[0]
            assert deriv            # because given as arg

            # find in our records.
            for (x_xfp, x_deriv, x_xpub) in self.xpubs:
                if x_xfp != xfp:
                    continue
                # found matching XFP
                assert deriv == x_deriv

                assert xpub_reserialized == x_xpub, 'xpub wrong (xfp=%s)' % xfp2str(xfp)
                break
            else:
                assert False            # not reachable, since we picked wallet based on xfps

    def get_deriv_paths(self):
        # List of unique derivation paths being used. Often length one.
        # - also a rendered single-value summary
        derivs = sorted(set(d for _, d, _ in self.xpubs))

        if len(derivs) == 1:
            dsum = derivs[0]
        else:
            dsum = 'Varies (%d)' % len(derivs)

        return derivs, dsum

    def format_overview(self):
        from utils import recolor
        from styles.colors import FD_BLUE_HEX, COPPER_HEX

        M, N = self.M, self.N

        if M == N == 1:
            exp = 'The one signer must approve transactions.'
        if M == N:
            exp = 'All {} co-signers must approve transactions.'.format(recolor(FD_BLUE_HEX, '%d' % N))
        elif M == 1:
            exp = 'Any signature from {} co-signers will approve transactions.'.format(recolor(FD_BLUE_HEX, '%d' % N))
        else:
            exp = '{M} signatures, from {N} possible co-signers, will be required to approve transactions.'.format(
                M=recolor(FD_BLUE_HEX, '%d' % M), N=recolor(FD_BLUE_HEX, '%d' % N))

        # Look for duplicate stuff
        name_change, diff_items, num_dups = self.has_similar()

        is_dup = False
        if name_change:
            msg = 'Update only the name of existing multisig config?'
        if diff_items:
            # Concern here is overwrite when similar, but we don't overwrite anymore, so
            # more of a warning about funny business.
            msg = '''\
{} This new wallet is similar to an existing wallet, but will NOT replace it. Consider deleting previous \
wallet first. Differences: '''.format(recolor(COPPER_HEX, 'WARNING:')) + ', '.join(diff_items)
            is_dup = True
        elif num_dups:
            msg = 'Duplicate wallet. All details are the same as an existing wallet, so it will not be added.'
            is_dup = True
        else:
            msg = 'Create new multisig wallet?'

        derivs, dsum = self.get_deriv_paths()

        msg += '''\n
{name_title}
{name}

{policy_title} {M} of {N}

{exp}

{addr_title}
{at}

{deriv_title}
  {dsum}'''.format(
            M=M,
            N=N,
            name_title=recolor(FD_BLUE_HEX, 'Wallet Name'),
            name=self.name,
            policy_title=recolor(FD_BLUE_HEX, 'Policy:'),
            exp=exp,
            addr_title=recolor(FD_BLUE_HEX, 'Addresses'),
            deriv_title=recolor(FD_BLUE_HEX, 'Derivation'),
            dsum=dsum,
            at=MultisigWallet.render_addr_fmt(self.addr_fmt))
        return msg, is_dup

    def format_details(self):
        import uio
        from utils import xfp2str
        from public_constants import AF_P2SH

        # Show the xpubs; might be 2k or more rendered.
        msg = uio.StringIO()

        #         if verbose:
        #             msg.write('''
        # Policy: {M} of {N}

        # Blockchain: {ctype}

        # Addresses:
        #   {at}\n\n'''.format(M=self.M, N=self.N, ctype=self.chain_type,
        #                      at=self.render_addr_fmt(self.addr_fmt)))

        # Concern: the order of keys here is non-deterministic
        for idx, (xfp, deriv, xpub) in enumerate(self.xpubs):
            if idx:
                msg.write('\n----------\n\n')

            msg.write('%s:\n  %s\n\n%s\n' % (xfp2str(xfp), deriv, xpub))

            if self.addr_fmt != AF_P2SH:
                # SLIP-132 format [yz]pubs here when not p2sh mode.
                # - has same info as proper bitcoin serialization, but looks much different
                node = self.chain.deserialize_node(xpub, AF_P2SH)
                xp = self.chain.serialize_public(node, self.addr_fmt)

                msg.write('\nSLIP-132 equiv:\n%s\n' % xp)

        return msg.getvalue()


def import_xpub(ln):
    # read an xpub/ypub/etc and return BIP32 node and what chain it's on.
    # - can handle any garbage line
    # - returns (node, chain, addr_fmt)
    # - people are using SLIP132 so we need this
    import chains
    import ure

    pat = ure.compile(r'.pub[A-Za-z0-9]+')

    found = pat.search(ln)
    if not found:
        return None

    found = found.group(0)

    for ch in chains.AllChains:
        for kk in ch.slip132:
            if found[0] == ch.slip132[kk].hint:
                try:
                    node = trezorcrypto.bip32.deserialize(found, ch.slip132[kk].pub, True)
                    chain = ch
                    addr_fmt = kk
                    return (node, ch, kk)
                except ValueError as e:
                    pass

    # looked like one, but failed to deserialize
    return None

# EOF
