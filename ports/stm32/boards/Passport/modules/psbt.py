# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# psbt.py - understand PSBT file format: verify and generate them
#
from ustruct import unpack_from, unpack, pack
from utils import xfp2str, B2A, keypath_to_str, swab32
import trezorcrypto
import gc
import history
import sys
from sffile import SizerFile
from passport import mem
from public_constants import MAX_SIGNERS
from multisig_wallet import MultisigWallet, disassemble_multisig_mn
from exceptions import FatalPSBTIssue, FraudulentChangeOutput
from serializations import ser_compact_size, deser_compact_size, hash160, deser_compact_size_bytes
from serializations import CTxIn, CTxInWitness, CTxOut, SIGHASH_ALL, VALID_SIGHASHES, SIGHASH_DEFAULT
from serializations import ser_push_data, uint256_from_bytes
from serializations import ser_string
from ubinascii import hexlify as b2a_hex
from taproot import output_script, tagged_hash

from public_constants import (
    PSBT_GLOBAL_UNSIGNED_TX, PSBT_GLOBAL_XPUB, PSBT_IN_NON_WITNESS_UTXO, PSBT_IN_WITNESS_UTXO,
    PSBT_IN_PARTIAL_SIG, PSBT_IN_SIGHASH_TYPE, PSBT_IN_REDEEM_SCRIPT,
    PSBT_IN_WITNESS_SCRIPT, PSBT_IN_BIP32_DERIVATION, PSBT_IN_FINAL_SCRIPTSIG,
    PSBT_IN_FINAL_SCRIPTWITNESS, PSBT_OUT_REDEEM_SCRIPT, PSBT_OUT_WITNESS_SCRIPT,
    PSBT_OUT_BIP32_DERIVATION, MAX_PATH_DEPTH, PSBT_IN_TAP_BIP32_DERIVATION,
    PSBT_OUT_TAP_BIP32_DERIVATION, PSBT_IN_TAP_KEY_SIG, PSBT_IN_TAP_SCRIPT_SIG,
    PSBT_IN_TAP_LEAF_SCRIPT, PSBT_IN_TAP_INTERNAL_KEY, PSBT_IN_TAP_MERKLE_ROOT,
    PSBT_OUT_TAP_INTERNAL_KEY, PSBT_OUT_TAP_TREE
)

# print some things
# DEBUG = const(1)

_MAGIC = b'psbt\xff'


def seq_to_str(seq):
    # take a set or list of numbers and show a tidy list in order.
    return ', '.join(str(i) for i in sorted(seq))


def _skip_n_objs(fd, n, cls):
    # skip N sized objects in the stream, for example a vectors of CTxIns
    # - returns starting position

    if cls == 'CTxIn':
        # output point(hash, n) + script sig + locktime
        pat = [32 + 4, None, 4]
    elif cls == 'CTxOut':
        # nValue + Script
        pat = [8, None]
    else:
        raise ValueError(cls)

    rv = fd.tell()
    for i in range(n):
        for p in pat:
            if p is None:
                # variable-length part
                sz = deser_compact_size(fd)
                fd.seek(sz, 1)
            else:
                fd.seek(p, 1)

    return rv


def calc_txid(fd, poslen, body_poslen=None):
    # Given the (pos,len) of a transaction in a file, return the txid for that txn.
    # - doesn't validate data
    # - does detect witness txn vs. old style
    # - simple double-sha256() if old style txn, otherwise witness data must be carefully skipped

    # see if witness encoding in effect
    fd.seek(poslen[0])

    txn_version, marker, flags = unpack("<iBB", fd.read(6))
    has_witness = (marker == 0 and flags != 0x0)

    if not has_witness:
        # txn does not have witness data, so txid==wtxix
        return get_hash256(fd, poslen)

    rv = trezorcrypto.sha256()

    # de/reserialize much of the txn -- but not the witness data
    rv.update(pack("<i", txn_version))

    if body_poslen is None:
        body_start = fd.tell()

        # determine how long ins + outs are...
        num_in = deser_compact_size(fd)
        _skip_n_objs(fd, num_in, 'CTxIn')
        num_out = deser_compact_size(fd)
        _skip_n_objs(fd, num_out, 'CTxOut')

        body_poslen = (body_start, fd.tell() - body_start)

    # hash the bulk of txn
    get_hash256(fd, body_poslen, hasher=rv)

    # assume last 4 bytes are the lock_time
    fd.seek(sum(poslen) - 4)

    rv.update(fd.read(4))

    return trezorcrypto.sha256(rv.digest()).digest()


def get_hash256(fd, poslen, hasher=None):
    # return the double-sha256 of a value, without loading it into memory
    pos, ll = poslen
    rv = hasher or trezorcrypto.sha256()

    fd.seek(pos)
    while ll:
        here = fd.readinto(mem.psbt_tmp256)
        if not here:
            break
        if here > ll:
            here = ll
        rv.update(memoryview(mem.psbt_tmp256)[0:here])
        ll -= here

    if hasher:
        return

    return trezorcrypto.sha256(rv.digest()).digest()


class psbtProxy:
    # store offsets to values, but track the keys in-memory.
    short_values = ()
    no_keys = ()

    # these fields will return None but are not stored unless a value is set
    blank_flds = ('unknown', 'subpaths', 'tap_subpaths')

    def __init__(self):
        self.fd = None
        self.unknown = {}

    def __getattr__(self, nm):
        if nm in self.blank_flds:
            return None
        raise AttributeError(nm)

    def parse(self, fd):
        self.fd = fd

        while True:
            ks = deser_compact_size(fd)
            if ks is None:
                break
            if ks == 0:
                break

            key = fd.read(ks)
            vs = deser_compact_size(fd)
            assert vs is not None, 'eof'

            kt = key[0]
            # print('kt={}'.format(kt))

            # print('self.no_keys={} 1'.format(self.no_keys))
            if kt in self.no_keys:
                # print('not expecting key')
                assert len(key) == 1        # not expecting key

            # storing offset and length only! Mostly.
            # print('self.short_values={}'.format(self.short_values))
            if kt in self.short_values:
                # print('Adding xpub')
                actual = fd.read(vs)

                self.store(kt, bytes(key), actual)
            else:
                # skip actual data for now
                proxy = (fd.tell(), vs)
                fd.seek(vs, 1)

                self.store(kt, bytes(key), proxy)

    def write(self, out_fd, ktype, val, key=b''):
        # serialize helper: write w/ size and key byte
        out_fd.write(ser_compact_size(1 + len(key)))
        out_fd.write(bytes([ktype]))
        out_fd.write(key)

        if isinstance(val, tuple):
            if ktype in (PSBT_IN_TAP_BIP32_DERIVATION, PSBT_OUT_TAP_BIP32_DERIVATION):
                path, tap_hashes = val
                output = ser_compact_size(len(tap_hashes))
                for h in tap_hashes:
                    output += h
                for element in path:
                    output += pack('<I', element)
                out_fd.write(ser_compact_size(len(output)))
                out_fd.write(output)
            else:
                (pos, ll) = val
                out_fd.write(ser_compact_size(ll))
                self.fd.seek(pos)
                while ll:
                    t = self.fd.read(min(64, ll))
                    out_fd.write(t)
                    ll -= len(t)

        elif isinstance(val, list):
            # for subpaths lists (LE32 ints)
            assert ktype in (PSBT_IN_BIP32_DERIVATION, PSBT_OUT_BIP32_DERIVATION)
            out_fd.write(ser_compact_size(len(val) * 4))
            for i in val:
                out_fd.write(pack('<I', i))
        else:
            out_fd.write(ser_compact_size(len(val)))
            out_fd.write(val)

    def get(self, val):
        # get the raw bytes for a value.
        pos, ll = val
        self.fd.seek(pos)
        return self.fd.read(ll)

    def parse_subpaths(self, my_xfp):
        # Reformat self.subpaths into a more useful form for us; return # of them
        # that are ours (and track that as self.num_our_keys)
        # - works in-place, on self.subpaths
        # - creates dictionary: pubkey => [xfp, *path]
        # - will be single entry for non-p2sh ins and outs

        if not self.subpaths and not self.tap_subpaths:
            return 0

        if self.num_our_keys is not None:
            # already been here once
            return self.num_our_keys

        num_ours = 0
        if self.subpaths:
            for pk in self.subpaths:
                assert len(pk) in {33, 65}, "hdpath pubkey len"
                if len(pk) == 33:
                    assert pk[0] in {0x02, 0x03}, "uncompressed pubkey"

                vl = self.subpaths[pk][1]

                # force them to use a derived key, never the master
                assert vl >= 8, 'too short key path'
                assert (vl % 4) == 0, 'corrupt key path'
                assert (vl // 4) <= MAX_PATH_DEPTH, 'too deep'

                # promote to a list of ints
                v = self.get(self.subpaths[pk])
                here = list(unpack_from('<%dI' % (vl // 4), v))

                # update in place
                self.subpaths[pk] = here

                if here[0] == my_xfp or here[0] == swab32(my_xfp):
                    num_ours += 1
                else:
                    # Address that isn't based on my seed; might be another leg in a p2sh,
                    # or an input we're not supposed to be able to sign... and that's okay.
                    pass

        if self.tap_subpaths:
            for pk in self.tap_subpaths:
                assert len(pk) == 32, "taproot hdpath pubkey len"

                vl = self.tap_subpaths[pk][1]

                # parse leaf hashes and path
                v = self.get(self.tap_subpaths[pk])
                (num_tap_hashes, compact_length) = deser_compact_size_bytes(v)
                tap_hashes = [uint256_from_bytes(v[i * 32:(i + 1) * 32]) for i in range(0, num_tap_hashes)]
                v = v[(num_tap_hashes * 32 + compact_length):]
                vl = len(v)

                # Master key can be used if there is no tapscript tree
                if tap_hashes:
                    assert vl >= 8, 'too short key path'
                assert (vl % 4) == 0, 'corrupt key path'
                assert (vl // 4) <= MAX_PATH_DEPTH, 'too deep'

                here = list(unpack_from('<%dI' % (vl // 4), v))

                # update in place
                self.tap_subpaths[pk] = (here, tap_hashes)

                if here[0] == my_xfp or here[0] == swab32(my_xfp):
                    num_ours += 1
                else:
                    # Address that isn't based on my seed; might be another leg in a p2sh,
                    # or an input we're not supposed to be able to sign... and that's okay.
                    pass

        self.num_our_keys = num_ours
        return num_ours


# Track details of each output of PSBT
#
class psbtOutputProxy(psbtProxy):
    no_keys = {PSBT_OUT_REDEEM_SCRIPT, PSBT_OUT_WITNESS_SCRIPT}
    blank_flds = ('unknown', 'subpaths', 'redeem_script', 'witness_script',
                  'is_change', 'num_our_keys', 'tap_internal_key', 'tap_tree',
                  'tap_subpaths')

    def __init__(self, fd, idx):
        super().__init__()

        # things we track
        # self.subpaths = None        # a dictionary if non-empty
        # self.tap_subpaths = None
        # self.redeem_script = None
        # self.witness_script = None

        # this flag is set when we are assuming output will be change (same wallet)
        # self.is_change = False

        self.parse(fd)

    def store(self, kt, key, val):
        if kt == PSBT_OUT_BIP32_DERIVATION:
            if not self.subpaths:
                self.subpaths = {}
            self.subpaths[key[1:]] = val
        elif kt == PSBT_OUT_REDEEM_SCRIPT:
            self.redeem_script = val
        elif kt == PSBT_OUT_WITNESS_SCRIPT:
            self.witness_script = val
        elif kt == PSBT_OUT_TAP_INTERNAL_KEY:
            self.tap_internal_key = val
        elif kt == PSBT_OUT_TAP_TREE:
            self.tap_tree = val
        elif kt == PSBT_OUT_TAP_BIP32_DERIVATION:
            if not self.tap_subpaths:
                self.tap_subpaths = {}
            self.tap_subpaths[key[1:]] = val
        else:
            self.unknown[key] = val

    def serialize(self, out_fd, my_idx):

        def wr(*a):
            self.write(out_fd, *a)

        if self.subpaths:
            for k in self.subpaths:
                wr(PSBT_OUT_BIP32_DERIVATION, self.subpaths[k], k)

        if self.redeem_script:
            wr(PSBT_OUT_REDEEM_SCRIPT, self.redeem_script)

        if self.witness_script:
            wr(PSBT_OUT_WITNESS_SCRIPT, self.witness_script)

        if self.tap_internal_key:
            wr(PSBT_OUT_TAP_INTERNAL_KEY, self.tap_internal_key)

        if self.tap_tree:
            wr(PSBT_OUT_TAP_TREE, self.tap_tree)

        if self.tap_subpaths:
            for k in self.tap_subpaths:
                wr(PSBT_OUT_TAP_BIP32_DERIVATION, self.tap_subpaths[k], k)

        for k in self.unknown:
            wr(k[0], self.unknown[k], k[1:])

    def validate(self, out_idx, txo, my_xfp, active_multisig):
        # Do things make sense for this output?

        # NOTE: We might think it's a change output just because the PSBT
        # creator has given us a key path. However, we must be **very**
        # careful and fully validate all the details.
        # - no output info is needed, in general, so
        #   any output info provided better be right, or fail as "fraud"
        # - full key derivation and validation is done during signing, and critical.
        # - we raise fraud alarms, since these are not innocent errors
        #

        num_ours = self.parse_subpaths(my_xfp)

        if num_ours == 0:
            # - not considered fraud because other signers looking at PSBT may have them
            # - user will see them as normal outputs, which they are from our PoV.
            return

        # - must match expected address for this output, coming from unsigned txn
        addr_type, addr_or_pubkey, is_segwit = txo.get_address()

        if self.subpaths and len(self.subpaths) == 1:
            # p2pk, p2pkh, p2wpkh cases
            expect_pubkey, = self.subpaths.keys()
        elif self.tap_subpaths and len(self.tap_subpaths) == 1:
            expect_pubkey, = self.tap_subpaths.keys()
        else:
            # p2wsh/p2sh cases need full set of pubkeys, and therefore redeem script
            expect_pubkey = None

        if addr_type == 'p2pk':
            # output is public key (not a hash, much less common)
            assert len(addr_or_pubkey) == 33

            if addr_or_pubkey != expect_pubkey:
                raise FraudulentChangeOutput(out_idx, "P2PK change output is fraudulent")

            self.is_change = True
            return

        # Figure out what the hashed addr should be
        pkh = addr_or_pubkey

        if addr_type == 'p2sh':
            # P2SH or Multisig output

            # Can be both, or either one depending on address type
            redeem_script = self.get(self.redeem_script) if self.redeem_script else None
            witness_script = self.get(self.witness_script) if self.witness_script else None

            if not redeem_script and not witness_script:
                # Perhaps an omission, so let's not call fraud on it
                # But definitely required, else we don't know what script we're sending to.
                raise FatalPSBTIssue("Missing redeem/witness script for output #%d" % out_idx)

            if not is_segwit and redeem_script and \
                    len(redeem_script) == 22 and \
                    redeem_script[0] == 0 and redeem_script[1] == 20:

                # it's actually segwit p2pkh inside p2sh
                pkh = redeem_script[2:22]
                expect_pkh = hash160(expect_pubkey)

            else:
                # Multisig change output, for wallet we're supposed to be a part of.
                # - our key must be part of it
                # - must look like input side redeem script (same fingerprints)
                # - assert M/N structure of output to match any inputs we have signed in PSBT!
                # - assert all provided pubkeys are in redeem script, not just ours
                # - we get all of that by re-constructing the script from our wallet details

                # it cannot be change if it doesn't precisely match our multisig setup
                if not active_multisig:
                    # - might be a p2sh output for another wallet that isn't us
                    # - not fraud, just an output with more details than we need.
                    self.is_change = False
                    return

                # redeem script must be exactly what we expect
                # - pubkeys will be reconstructed from derived paths here
                # - BIP45, BIP67 rules applied
                # - p2sh-p2wsh needs witness script here, not redeem script value
                # - if details provided in output section, must our match multisig wallet
                try:
                    active_multisig.validate_script(witness_script or redeem_script,
                                                    subpaths=self.subpaths)
                except BaseException as exc:
                    raise FraudulentChangeOutput(out_idx,
                                                 "P2WSH or P2SH change output script: %s" % exc)

                if is_segwit:
                    # p2wsh case
                    # - need witness script and check it's hash against proposed p2wsh value
                    assert len(addr_or_pubkey) == 32
                    expect_wsh = trezorcrypto.sha256(witness_script).digest()
                    if expect_wsh != addr_or_pubkey:
                        raise FraudulentChangeOutput(out_idx, "P2WSH witness script has wrong hash")

                    self.is_change = True
                    return

                if witness_script:
                    # p2sh-p2wsh case (because it had witness script)
                    expect_rs = b'\x00\x20' + trezorcrypto.sha256(witness_script).digest()

                    if redeem_script and expect_rs != redeem_script:
                        # iff they provide a redeeem script, then it needs to match
                        # what we expect it to be
                        raise FraudulentChangeOutput(out_idx,
                                                     "P2SH-P2WSH redeem script provided, and doesn't match")

                    expect_pkh = hash160(expect_rs)
                else:
                    # old BIP16 style; looks like payment addr
                    expect_pkh = hash160(redeem_script)

        elif addr_type == 'p2pkh':
            # input is hash160 of a single public key
            assert len(addr_or_pubkey) == 20
            expect_pkh = hash160(expect_pubkey)
        elif addr_type == 'p2tr':
            expect_pkh = output_script(expect_pubkey, None)[2:]
        else:
            # we don't know how to "solve" this type of input
            return

        if pkh != expect_pkh:
            raise FraudulentChangeOutput(out_idx, "Change output is fraudulent")

        # We will check pubkey value at the last second, during signing.
        self.is_change = True


# Track details of each input of PSBT
#
class psbtInputProxy(psbtProxy):

    # just need to store a simple number for these
    short_values = {PSBT_IN_SIGHASH_TYPE}

    # only part-sigs have a key to be stored.
    no_keys = {PSBT_IN_NON_WITNESS_UTXO, PSBT_IN_WITNESS_UTXO, PSBT_IN_SIGHASH_TYPE,
               PSBT_IN_REDEEM_SCRIPT, PSBT_IN_WITNESS_SCRIPT, PSBT_IN_FINAL_SCRIPTSIG,
               PSBT_IN_FINAL_SCRIPTWITNESS, PSBT_IN_TAP_KEY_SIG, PSBT_IN_TAP_INTERNAL_KEY,
               PSBT_IN_TAP_MERKLE_ROOT}

    blank_flds = ('unknown',
                  'utxo', 'witness_utxo', 'sighash',
                  'redeem_script', 'witness_script', 'fully_signed',
                  'is_segwit', 'is_multisig', 'is_p2sh', 'num_our_keys',
                  'required_key', 'scriptSig', 'amount', 'scriptCode', 'added_sig',
                  'tap_internal_key', 'tap_key_sig', 'tap_merkle_root')

    def __init__(self, fd, idx):
        super().__init__()

        # self.utxo = None
        # self.witness_utxo = None
        self.part_sig = {}
        # self.sighash = None
        self.subpaths = {}          # will typically be non-empty for all inputs
        self.tap_subpaths = {}
        self.tap_script_sigs = {}
        self.tap_leaf_scripts = {}
        # self.redeem_script = None
        # self.witness_script = None

        # Non-zero if one or more of our signing keys involved in input
        # self.num_our_keys = None

        # things we've learned
        # self.fully_signed = False

        # we can't really learn this until we take apart the UTXO's scriptPubKey
        # self.is_segwit = None
        # self.is_multisig = None
        # self.is_p2sh = False

        # self.required_key = None    # which of our keys will be used to sign input
        # self.scriptSig = None
        # self.amount = None
        # self.scriptCode = None      # only expected for segwit inputs

        # after signing, we'll have a signature to add to output PSBT
        # self.added_sig = None
        # self.tap_key_sig = None

        self.parse(fd)
        gc.collect()

    def validate(self, idx, txin, my_xfp):
        # Validate this txn input: given deserialized CTxIn and maybe witness

        # TODO: tighten these
        if self.witness_script:
            assert self.witness_script[1] >= 30
        if self.redeem_script:
            assert self.redeem_script[1] >= 22

        # require path for each addr, check some are ours

        # rework the pubkey => subpath mapping
        self.parse_subpaths(my_xfp)

        # sighash, but we're probably going to ignore anyway.
        if self.sighash is None:
            # Taproot PSBTs can be built with no explicit sighash
            if len(self.tap_subpaths) > 0:
                self.sighash = SIGHASH_DEFAULT
            else:
                self.sighash = SIGHASH_ALL

        if self.sighash not in VALID_SIGHASHES:
            # - someday we will expand to other types, but not yet
            raise FatalPSBTIssue('Can only do SIGHASH_ALL')

        if self.part_sig:
            # How complete is the set of signatures so far?
            # - assuming PSBT creator doesn't give us extra data not required
            # - seems harmless if they fool us into thinking already signed; we do nothing
            # - could also look at pubkey needed vs. sig provided
            # - could consider structure of MofN in p2sh cases
            num_subpaths = len(self.tap_subpaths) if len(self.tap_subpaths) > 0 else len(self.subpaths)
            self.fully_signed = len(self.part_sig) >= num_subpaths
        else:
            # No signatures at all yet for this input (typical non multisig)
            self.fully_signed = False

        if self.utxo:
            # Important: they might be trying to trick us with an un-related
            # funding transaction (UTXO) that does not match the input signature we're making
            # (but if it's segwit, the ploy wouldn't work, Segwit FtW)
            # - challenge: it's a straight dsha256() for old serializations, but not for newer
            #   segwit txn's... plus I don't want to deserialize it here.
            try:
                observed = uint256_from_bytes(calc_txid(self.fd, self.utxo))
            except BaseException:
                raise AssertionError("Trouble parsing UTXO given for input #%d" % idx)

            assert txin.prevout.hash == observed, "utxo hash mismatch for input #%d" % idx

    def has_utxo(self):
        # do we have a copy of the corresponding UTXO?
        return bool(self.utxo) or bool(self.witness_utxo)

    def get_utxo(self, idx):
        # Load up the TxOut for specific output of the input txn associated with this in PSBT
        # Aka. the "spendable" for this input #.
        # - preserve the file pointer
        # - nValue needed for total_value_in, but all fields needed for signing
        #
        fd = self.fd
        old_pos = fd.tell()

        if self.witness_utxo:
            # Going forward? Just what we will witness; no other junk
            # - prefer this format, altho does that imply segwit txn must be generated?
            # - I don't know why we wouldn't always use this
            # - once we use this partial utxo data, we must create witness data out
            self.is_segwit = True

            fd.seek(self.witness_utxo[0])
            utxo = CTxOut()
            utxo.deserialize(fd)
            fd.seek(old_pos)

            return utxo

        assert self.utxo, 'no utxo'

        # skip over all the parts of the txn we don't care about, without
        # fully parsing it... pull out a single TXO
        fd.seek(self.utxo[0])

        _, marker, flags = unpack("<iBB", fd.read(6))
        wit_format = (marker == 0 and flags != 0x0)
        if not wit_format:
            # rewind back over marker+flags
            fd.seek(-2, 1)

        # How many ins? We accept zero here because utxo's inputs might have been
        # trimmed to save space, and we have test cases like that.
        num_in = deser_compact_size(fd)
        _skip_n_objs(fd, num_in, 'CTxIn')

        num_out = deser_compact_size(fd)
        assert idx < num_out, "not enuf outs"
        _skip_n_objs(fd, idx, 'CTxOut')

        utxo = CTxOut()
        utxo.deserialize(fd)

        # ... followed by more outs, and maybe witness data, but we don't care ...

        fd.seek(old_pos)

        return utxo

    def determine_my_signing_key(self, my_idx, utxo, my_xfp, psbt):
        # See what it takes to sign this particular input
        # - type of script
        # - which pubkey needed
        # - scriptSig value
        # - also validates redeem_script when present

        self.amount = utxo.nValue

        if (not self.subpaths and not self.tap_subpaths) or self.fully_signed:
            # without xfp+path we will not be able to sign this input
            # - okay if fully signed
            # - okay if payjoin or other multi-signer (not multisig) txn
            self.required_key = None
            return

        self.is_multisig = False
        self.is_p2sh = False
        which_key = None

        addr_type, addr_or_pubkey, addr_is_segwit = utxo.get_address()
        if addr_is_segwit and not self.is_segwit:
            self.is_segwit = True

        if addr_type == 'p2sh':
            # multisig input
            self.is_p2sh = True

            # we must have the redeem script already (else fail)
            ks = self.witness_script or self.redeem_script
            if not ks:
                raise FatalPSBTIssue("Missing redeem/witness script for input #%d" % my_idx)

            redeem_script = self.get(ks)
            self.scriptSig = redeem_script

            # new cheat: psbt creator probably telling us exactly what key
            # to use, by providing exactly one. This is ideal for p2sh wrapped p2pkh
            if len(self.subpaths) == 1:
                which_key, = self.subpaths.keys()
            else:
                # Assume we'll be signing with any key we know
                # - limitation: we cannot be two legs of a multisig
                # - but if partial sig already in place, ignore that one
                for pubkey, path in self.subpaths.items():
                    if self.part_sig and (pubkey in self.part_sig):
                        # pubkey has already signed, so ignore
                        continue

                    if path[0] == my_xfp or path[0] == swab32(my_xfp):
                        # slight chance of dup xfps, so handle
                        if not which_key:
                            which_key = set()

                        which_key.add(pubkey)

            if not addr_is_segwit and \
                    len(redeem_script) == 22 and \
                    redeem_script[0] == 0 and redeem_script[1] == 20:
                # it's actually segwit p2pkh inside p2sh
                addr_type = 'p2sh-p2wpkh'
                addr = redeem_script[2:22]
                self.is_segwit = True
            else:
                # multiple keys involved, we probably can't do the finalize step
                self.is_multisig = True

            if self.witness_script and not self.is_segwit and self.is_multisig:
                # bugfix
                addr_type = 'p2sh-p2wsh'
                self.is_segwit = True

        elif addr_type == 'p2pkh':
            # input is hash160 of a single public key
            self.scriptSig = utxo.scriptPubKey
            addr = addr_or_pubkey

            for pubkey in self.subpaths:
                if hash160(pubkey) == addr:
                    which_key = pubkey
                    break

        elif addr_type == 'p2pk':
            # input is single public key (less common)
            self.scriptSig = utxo.scriptPubKey
            assert len(addr_or_pubkey) == 33

            if addr_or_pubkey in self.subpaths:
                which_key = addr_or_pubkey

        elif addr_type == 'p2tr':
            # input is an x-only public key or merkle tree root
            # TODO: handle tapscript tree
            self.scriptSig = utxo.scriptPubKey

            if len(self.tap_subpaths) == 1:  # No script path
                subpath = list(self.tap_subpaths.items())[0]
                pubkey, (path, tap_hashes) = subpath
                tweaked_pubkey = output_script(pubkey, None)[2:]
                if path[0] == my_xfp and tweaked_pubkey == addr_or_pubkey:
                    which_key = pubkey
        else:
            # we don't know how to "solve" this type of input
            pass

        if self.is_multisig and which_key:
            # We will be signing this input, so
            # - find which wallet it is or
            # - check it's the right M/N to match redeem script

            # print("redeem: %s" % b2a_hex(redeem_script))
            M, N = disassemble_multisig_mn(redeem_script)
            xfp_paths = sorted(self.subpaths.values())

            if not psbt.active_multisig:
                # search for multisig wallet
                wal = MultisigWallet.find_match(M, N, xfp_paths)
                if not wal:
                    raise FatalPSBTIssue('Unknown multisig wallet')

                psbt.active_multisig = wal
            else:
                # check consistent w/ already selected wallet
                psbt.active_multisig.assert_matching(M, N, xfp_paths)

            # validate redeem script, by disassembling it and checking all pubkeys
            try:
                psbt.active_multisig.validate_script(redeem_script, subpaths=self.subpaths)
            except BaseException as exc:
                sys.print_exception(exc)
                raise FatalPSBTIssue('Input #%d: %s' % (my_idx, exc))

        # if not which_key and DEBUG:
        #     print("no key: input #%d: type=%s segwit=%d a_or_pk=%s scriptPubKey=%s" % (
        #             my_idx, addr_type, self.is_segwit or 0,
        #             b2a_hex(addr_or_pubkey), b2a_hex(utxo.scriptPubKey)))

        self.required_key = which_key

        if self.is_segwit:
            if ('pkh' in addr_type):
                # This comment from <https://bitcoincore.org/en/segwit_wallet_dev/>:
                #
                #   Please note that for a P2SH-P2WPKH, the scriptCode is always 26
                #   bytes including the leading size byte, as 0x1976a914{20-byte keyhash}88ac,
                #   NOT the redeemScript nor scriptPubKey
                #
                # Also need this scriptCode for native segwit p2pkh
                #
                assert not self.is_multisig
                self.scriptCode = b'\x19\x76\xa9\x14' + addr + b'\x88\xac'
            elif addr_type == 'p2tr':
                pass
            elif not self.scriptCode:
                # Segwit P2SH. We need the witness script to be provided.
                if not self.witness_script:
                    raise FatalPSBTIssue('Need witness script for input #%d' % my_idx)

                # "scriptCode is witnessScript preceeded by a
                #  compactSize integer for the size of witnessScript"
                self.scriptCode = ser_string(self.get(self.witness_script))

        # Could probably free self.subpaths and self.redeem_script now, but only if we didn't
        # need to re-serialize as a PSBT.

    def store(self, kt, key, val):
        # Capture what we are interested in.

        if kt == PSBT_IN_NON_WITNESS_UTXO:
            self.utxo = val
        elif kt == PSBT_IN_WITNESS_UTXO:
            self.witness_utxo = val
        elif kt == PSBT_IN_PARTIAL_SIG:
            self.part_sig[key[1:]] = val
        elif kt == PSBT_IN_BIP32_DERIVATION:
            self.subpaths[key[1:]] = val
        elif kt == PSBT_IN_REDEEM_SCRIPT:
            self.redeem_script = val
        elif kt == PSBT_IN_WITNESS_SCRIPT:
            self.witness_script = val
        elif kt == PSBT_IN_SIGHASH_TYPE:
            self.sighash = unpack('<I', val)[0]
        elif kt == PSBT_IN_TAP_KEY_SIG:
            self.tap_key_sig = val
        elif kt == PSBT_IN_TAP_SCRIPT_SIG:
            self.tap_script_sigs[key[1:]] = val
        elif kt == PSBT_IN_TAP_LEAF_SCRIPT:
            self.tap_leaf_scripts[key[1:]] = val
        elif kt == PSBT_IN_TAP_BIP32_DERIVATION:
            self.tap_subpaths[key[1:]] = val
        elif kt == PSBT_IN_TAP_INTERNAL_KEY:
            self.tap_internal_key = val
        elif kt == PSBT_IN_TAP_MERKLE_ROOT:
            self.tap_merkle_root = val
        else:
            # including: PSBT_IN_FINAL_SCRIPTSIG, PSBT_IN_FINAL_SCRIPTWITNESS
            self.unknown[key] = val

    def serialize(self, out_fd, my_idx):
        # Output this input's values; might include signatures that weren't there before

        def wr(*a):
            self.write(out_fd, *a)

        if self.utxo:
            wr(PSBT_IN_NON_WITNESS_UTXO, self.utxo)
        if self.witness_utxo:
            wr(PSBT_IN_WITNESS_UTXO, self.witness_utxo)

        if self.part_sig:
            for pk in self.part_sig:
                wr(PSBT_IN_PARTIAL_SIG, self.part_sig[pk], pk)

        if self.added_sig:
            pubkey, sig = self.added_sig
            wr(PSBT_IN_PARTIAL_SIG, sig, pubkey)

        if self.sighash is not None:
            wr(PSBT_IN_SIGHASH_TYPE, pack('<I', self.sighash))

        for k in self.subpaths:
            wr(PSBT_IN_BIP32_DERIVATION, self.subpaths[k], k)

        if self.redeem_script:
            wr(PSBT_IN_REDEEM_SCRIPT, self.redeem_script)

        if self.witness_script:
            wr(PSBT_IN_WITNESS_SCRIPT, self.witness_script)

        if self.tap_key_sig:
            wr(PSBT_IN_TAP_KEY_SIG, self.tap_key_sig)

        for k in self.tap_subpaths:
            wr(PSBT_IN_TAP_BIP32_DERIVATION, self.tap_subpaths[k], k)

        if self.tap_internal_key:
            wr(PSBT_IN_TAP_INTERNAL_KEY, self.tap_internal_key)

        for k in self.unknown:
            wr(k[0], self.unknown[k], k[1:])


class psbtObject(psbtProxy):
    "Just? parse and store"

    no_keys = {PSBT_GLOBAL_UNSIGNED_TX}

    def __init__(self):
        super().__init__()

        # global objects
        self.txn = None
        self.xpubs = []         # tuples(xfp_path, xpub)

        from common import settings
        self.my_xfp = settings.get('xfp', 0)

        # details that we discover as we go
        self.inputs = None
        self.outputs = None
        self.had_witness = None
        self.num_inputs = None
        self.num_outputs = None
        self.vin_start = None
        self.vout_start = None
        self.wit_start = None
        self.txn_version = None
        self.lock_time = None
        self.total_value_out = None
        self.total_value_in = None
        self.presigned_inputs = set()
        self.multisig_import_needs_approval = False
        self.self_send = False

        # when signing segwit stuff, there is some re-use of hashes
        self.hashPrevouts = None
        self.hashSequence = None
        self.hashOutputs = None

        # taproot additions to reused segwit hashes
        self.hashAmounts = None
        self.hashScriptPubkeys = None

        # this points to a MS wallet, during operation
        # - we are only supporting a single multisig wallet during signing
        self.active_multisig = None

        self.warnings = []

    def store(self, kt, key, val):
        # capture the values we care about

        if kt == PSBT_GLOBAL_UNSIGNED_TX:
            self.txn = val
        elif kt == PSBT_GLOBAL_XPUB:
            # list of tuples(xfp_path, xpub)
            self.xpubs.append((self.get(val), key[1:]))
            assert len(self.xpubs) <= MAX_SIGNERS
        else:
            self.unknowns[key] = val

    def output_iter(self):
        # yield the txn's outputs: index, (CTxOut object) for each
        assert self.vout_start is not None      # must call input_iter/validate first

        fd = self.fd
        fd.seek(self.vout_start)

        total_out = 0
        tx_out = CTxOut()
        for idx in range(self.num_outputs):

            tx_out.deserialize(fd)

            total_out += tx_out.nValue

            cont = fd.tell()
            yield idx, tx_out

            fd.seek(cont)

        if self.total_value_out is None:
            self.total_value_out = total_out
        else:
            assert self.total_value_out == total_out

    def parse_txn(self):
        # Need to semi-parse in unsigned transaction.
        # - learn number of ins/outs so rest of PSBT can be understood
        # - also captures lots of position details
        # - called right after globals section is read
        fd = self.fd
        old_pos = fd.tell()
        fd.seek(self.txn[0])

        # see serializations.py:CTransaction.deserialize()
        # and BIP-144 ... we expect witness serialization, but
        # don't force that

        self.txn_version, marker, flags = unpack("<iBB", fd.read(6))
        self.had_witness = (marker == 0 and flags != 0x0)

        assert self.txn_version in {1, 2}, "bad txn version"

        if not self.had_witness:
            # rewind back over marker+flags
            fd.seek(-2, 1)

        num_in = deser_compact_size(fd)
        assert num_in > 0, "no ins?"

        self.num_inputs = num_in
        # print('self.num_inputs = {}'.format(self.num_inputs ))

        # all the ins are in sequence starting at this position
        self.vin_start = _skip_n_objs(fd, num_in, 'CTxIn')

        # next is outputs
        self.num_outputs = deser_compact_size(fd)
        # print('self.num_outputs = {}'.format(self.num_outputs ))

        self.vout_start = _skip_n_objs(fd, self.num_outputs, 'CTxOut')

        end_pos = sum(self.txn)

        # remainder is the witness data, and then the lock time

        if self.had_witness:
            # we'll need to come back to this pos if we
            # want to read the witness data later.
            self.wit_start = _skip_n_objs(fd, num_in, 'CTxInWitness')

        # we are at end of outputs, and no witness data, so locktime is here
        self.lock_time = unpack("<I", fd.read(4))[0]

        assert fd.tell() == end_pos, 'txn read end wrong'

        fd.seek(old_pos)

    def input_iter(self):
        # Yield each of the txn's inputs, as a tuple:
        #
        #   (index, CTxIn)
        #
        # - we also capture much data about the txn on the first pass thru here
        #
        fd = self.fd

        assert self.vin_start       # call parse_txn() first!

        # stream out the inputs
        fd.seek(self.vin_start)

        txin = CTxIn()
        for idx in range(self.num_inputs):
            txin.deserialize(fd)

            cont = fd.tell()
            yield idx, txin

            fd.seek(cont)

    def input_witness_iter(self):
        # yield all the witness data, in order by input
        if not self.had_witness:
            # original txn had no witness data, so provide placeholder objs
            for in_idx in range(self.num_inputs):
                yield in_idx, CTxInWitness()
            return

        fd.seek(self.wit_start)
        for idx in range(num_in):

            wit = CTxInWitness()
            wit.deserialize(fd)

            cont = fd.tell()
            yield idx, wit

            fd.seek(cont)

    def guess_M_of_N(self):
        # Peek at the inputs to see if we can guess M/N value. Just takes
        # first one it finds.
        #
        from opcodes import OP_CHECKMULTISIG
        for i in self.inputs:
            ks = i.witness_script or i.redeem_script
            if not ks:
                continue

            rs = i.get(ks)
            if rs[-1] != OP_CHECKMULTISIG:
                continue

            M, N = disassemble_multisig_mn(rs)
            assert 1 <= M <= N <= MAX_SIGNERS

            return (M, N)

        # not multisig, probably
        return None, None

    async def handle_xpubs(self):
        # Lookup correct wallet based on xpubs in globals
        # - only happens if they volunteered this 'extra' data
        # - do not assume multisig
        assert not self.active_multisig

        xfp_paths = []
        has_mine = 0
        for k, _ in self.xpubs:
            h = unpack_from('<%dI' % (len(k) // 4), k, 0)
            assert len(h) >= 1
            xfp_paths.append(h)

            if h[0] == self.my_xfp:
                has_mine += 1

        if not has_mine:
            raise FatalPSBTIssue('My XFP not involved')

        candidates = MultisigWallet.find_candidates(xfp_paths)

        if len(candidates) == 1:
            # exact match (by xfp+deriv set) .. normal case
            self.active_multisig = candidates[0]
        else:
            # don't want to guess M if not needed, but we need it
            M, N = self.guess_M_of_N()

            if not N:
                # not multisig, but we can still verify:
                # - XFP should be one of ours (checked above).
                # - too slow to re-derive it here, so nothing more to validate at this point
                return

            assert N == len(xfp_paths)

            for c in candidates:
                if c.M == M:
                    assert c.N == N
                    self.active_multisig = c
                    break

        del candidates

        if not self.active_multisig:
            # Maybe create wallet, for today, forever, or fail, etc.
            proposed, need_approval = MultisigWallet.import_from_psbt(M, N, self.xpubs)

            # print('proposed={}, need_approval={}'.format(proposed, need_approval))

            # Gen1.2 We don't do the UI part of this here, but in SignPsbtCommonFlow

            if need_approval:
                self.multisig_import_needs_approval = True
            #     # do a complex UX sequence, which lets them save new wallet
            #     ch = await proposed.confirm_import()
            #     if ch != 'y':
            #         raise FatalPSBTIssue("Refused to import new wallet")
            self.active_multisig = proposed
        else:
            # Validate good match here. The xpubs must be exactly right, but
            # we're going to use our own values from setup time anyway and not trusting
            # new values without user interaction.
            # Check:
            # - chain codes match what we have stored already
            # - pubkey vs. path will be checked later
            # - xfp+path already checked above when selecting wallet
            # Any issue here is a fraud attempt in some way, not innocent.
            self.active_multisig.validate_psbt_xpubs(self.xpubs)

        if not self.active_multisig:
            # not clear if an error... might be part-way to importing, and
            # the data is optional anyway, etc. If they refuse to import,
            # we should not reach this point (ie. raise something to abort signing)
            return

    async def validate(self):
        # Do a first pass over the txn. Raise assertions, be terse tho because
        # these messages are rarely seen. These are syntax/fatal errors.
        #
        assert self.txn[1] > 63, 'too short'

        # this parses the input TXN in-place
        for idx, txin in self.input_iter():
            gc.collect()
            self.inputs[idx].validate(idx, txin, self.my_xfp)

        gc.collect()

        assert len(self.inputs) == self.num_inputs, 'ni mismatch'

        # if multisig xpub details provided, they better be right and/or offer import
        # print('self.xpubs={}'.format(self.xpubs))
        if self.xpubs:
            # print('calling self.handle_xpubs()')
            await self.handle_xpubs()

        gc.collect()

        assert self.num_outputs >= 1, 'need outs'

        # if DEBUG:
        #     our_keys = sum(1 for i in self.inputs if i.num_our_keys)
        #
        #     print("PSBT: %d inputs, %d output, %d fully-signed, %d ours" % (
        #            self.num_inputs, self.num_outputs,
        #            sum(1 for i in self.inputs if i and i.fully_signed), our_keys))

    def consider_outputs(self):
        # scan ouputs:
        # - is it a change address, defined by redeem script (p2sh) or key we know is ours
        # - mark change outputs, so perhaps we don't show them to users

        total_change = 0
        # print('len(self.outputs)={}'.format(len(self.outputs)))
        for idx, txo in self.output_iter():
            self.outputs[idx].validate(idx, txo, self.my_xfp, self.active_multisig)

            if self.outputs[idx].is_change:
                total_change += txo.nValue

        if self.total_value_out is None:
            # this happens, but would expect this to have done already?
            for out_idx, txo in self.output_iter():
                pass

        # check fee is reasonable
        total_non_change_out = self.total_value_out - total_change
        # print('total_non_change_out={} self.total_value_out={}  total_change={}'.format(total_non_change_out,
        #       self.total_value_out, total_change))
        fee = self.calculate_fee()
        if self.total_value_out == 0:
            per_fee = 100
        elif total_non_change_out == 0:
            self.self_send = True
        else:
            # Calculate fee based on non-change output value
            per_fee = (fee / total_non_change_out) * 100

        if self.self_send:
            # self.warnings.append(('Self-Send', 'All outputs are being sent back to this wallet.'))
            per_fee = (fee / self.total_value_out) * 100
            if per_fee >= 5:
                self.warnings.append(('Big Fee', 'Network fee is more than '
                                      '5%% of total non-change value (%.1f%%).' % per_fee))
        else:
            if fee > total_non_change_out:
                self.warnings.append(('Huge Fee', 'Network fee is larger than the amount you are sending.'))
            elif per_fee >= 5:
                self.warnings.append(('Big Fee', 'Network fee is more than '
                                      '5%% of total non-change value (%.1f%%).' % per_fee))

        # Enforce policy related to change outputs
        self.consider_dangerous_change(self.my_xfp)

    def consider_dangerous_change(self, my_xfp):
        # Enforce some policy on change outputs:
        # - need to "look like" they are going to same wallet as inputs came from
        # - range limit last two path components (numerically)
        # - same pattern of hard/not hardened components
        # - MAX_PATH_DEPTH already enforced before this point
        #
        in_paths = []
        for inp in self.inputs:
            if inp.fully_signed:
                continue
            if not inp.required_key:
                continue
            if not inp.subpaths:
                continue        # not expected if we're signing it
            for path in inp.subpaths.values():
                if path[0] == my_xfp:
                    in_paths.append(path[1:])

        if not in_paths:
            # We aren't adding any signatures? Can happen but we're going to be
            # showing a warning about that elsewhere.
            return

        shortest = min(len(i) for i in in_paths)
        longest = max(len(i) for i in in_paths)
        if shortest != longest or shortest <= 2:
            # We aren't seeing shared input path lengths.
            # They are probbably doing weird stuff, so leave them alone.
            return

        # Assumption: hard/not hardened depths will match for all address in wallet
        def hard_bits(p):
            return [bool(i & 0x80000000) for i in p]

        # Assumption: common wallets modulate the last two components only
        # of the path. Typically m/.../change/index where change is {0, 1}
        # and index changes slowly over lifetime of wallet (increasing)
        path_len = shortest
        path_prefix = in_paths[0][0:-2]
        idx_max = max(i[-1] & 0x7fffffff for i in in_paths) + 200
        hard_pattern = hard_bits(in_paths[0])

        probs = []
        for nout, out in enumerate(self.outputs):
            if not out.is_change:
                continue
            # it's a change output, okay if a p2sh change; we're looking at paths
            for path in out.subpaths.values():
                if path[0] != my_xfp:
                    continue          # possible in p2sh case

                path = path[1:]
                if len(path) != path_len:
                    iss = "has wrong path length (%d not %d)" % (len(path), path_len)
                elif hard_bits(path) != hard_pattern:
                    iss = "has different hardening pattern"
                elif path[0:len(path_prefix)] != path_prefix:
                    iss = "goes to different path prefix"
                elif (path[-2] & 0x7fffffff) not in {0, 1}:
                    iss = "second last component not 0 or 1"
                elif (path[-1] & 0x7fffffff) > idx_max:
                    iss = "last component beyond reasonable gap"
                else:
                    # looks ok
                    continue

                probs.append("Output #%d: %s: %s not %s/{0~1}%s/{0~%d}%s expected"
                             % (nout, iss, keypath_to_str(path, skip=0),
                                keypath_to_str(path_prefix, skip=0),
                                "'" if hard_pattern[-2] else "",
                                idx_max, "'" if hard_pattern[-1] else "",
                                ))
                break

        for p in probs:
            self.warnings.append(('Suspicious Change Outputs', p))

    def consider_inputs(self):
        # Look an the UTXO's that we are spending. Do we have them? Do the
        # hashes match, and what values are we getting?
        # Important: parse incoming UTXO to build total input value
        missing = 0
        total_in = 0

        for i, txi in self.input_iter():
            gc.collect()
            inp = self.inputs[i]
            if inp.fully_signed:
                self.presigned_inputs.add(i)

            if not inp.has_utxo():
                # maybe they didn't provide the UTXO
                missing += 1
                continue

            # pull out just the CTXOut object (expensive)
            utxo = inp.get_utxo(txi.prevout.n)

            assert utxo.nValue > 0
            total_in += utxo.nValue

            # Look at what kind of input this will be, and therefore what
            # type of signing will be required, and which key we need.
            # - also validates redeem_script when present
            # - also finds appropriate multisig wallet to be used
            inp.determine_my_signing_key(i, utxo, self.my_xfp, self)

            gc.collect()

            # iff to UTXO is segwit, then check it's value, and also
            # capture that value, since it's supposed to be immutable
            if inp.is_segwit:
                history.verify_amount(txi.prevout, inp.amount, i)
                gc.collect()

            del utxo

        gc.collect()

        # XXX scan witness data provided, and consider those ins signed if not multisig?

        if missing:
            # Should probably be a fatal msg; so risky... but
            # - maybe we aren't expected to sign that input? (coinjoin)
            # - assume for now, probably funny business so we should stop
            raise FatalPSBTIssue('Missing UTXO(s). Cannot determine value being signed.')
            # self.warnings.append(('Missing UTXOs',
            #        "We don't know enough about the inputs to this transaction to be sure "
            #        "of their value. This means the network fee could be huge, or resulting "
            #        "transaction's signatures invalid."))
            # self.total_value_in = None
        else:
            assert total_in > 0
            self.total_value_in = total_in

        if len(self.presigned_inputs) == self.num_inputs:
            # Maybe wrong for multisig cases? Maybe they want to add their
            # own signature, even tho N of M is satisfied?!
            raise FatalPSBTIssue('Transaction is already fully signed.')

        # We should know pubkey required for each input now.
        # - but we may not be the signer for those inputs, which is fine.
        # - TODO: but what if not SIGHASH_ALL
        no_keys = set(n for n, inp in enumerate(self.inputs)
                      if inp.required_key is None and not inp.fully_signed)

        gc.collect()

        if no_keys:
            # This is seen when you re-sign same signed file by accident (multisig)
            # - case of len(no_keys)==num_inputs is handled by consider_keys
            self.warnings.append(
                ('Already Signed',
                 'Passport has already signed this transaction. Other signatures are still required.'))

            gc.collect()

        if self.presigned_inputs:
            # this isn't really even an issue for some complex usage cases
            self.warnings.append(('Partially Signed Already',
                                  'Some input(s) provided were already signed by other parties: ' +
                                  seq_to_str(self.presigned_inputs)))
            gc.collect()

    def calculate_fee(self):
        # what miner's reward is included in txn?
        if self.total_value_in is None:
            # print('Very odd that a txn has no total_value_in!  psbt={}'.format(self))
            return None

        return self.total_value_in - self.total_value_out

    def consider_keys(self):
        # check we possess the right keys for the inputs
        cnt = sum(1 for i in self.inputs if i.num_our_keys)
        if cnt:
            return

        # collect a list of XFP's given in file that aren't ours
        others = set()
        for inp in self.inputs:
            if not inp.subpaths:
                continue
            for path in inp.subpaths.values():
                others.add(path[0])

        others.discard(self.my_xfp)
        msg = ', '.join(xfp2str(i) for i in others)

        raise FatalPSBTIssue('None of the keys involved in this transaction '
                             'belong to this Passport (need %s, found %s).'
                             % (msg, xfp2str(self.my_xfp)))

    @classmethod
    def read_psbt(cls, fd):
        # read in a PSBT file. Captures fd and keeps it open.
        hdr = fd.read(5)
        if hdr != _MAGIC:
            raise ValueError("bad hdr")

        gc.collect()

        rv = cls()

        gc.collect()

        # read main body (globals)
        rv.parse(fd)

        gc.collect()

        assert rv.txn, 'missing reqd section'

        # learn about the bitcoin transaction we are signing.
        rv.parse_txn()

        gc.collect()

        rv.inputs = [psbtInputProxy(fd, idx) for idx in range(rv.num_inputs)]
        gc.collect()
        rv.outputs = [psbtOutputProxy(fd, idx) for idx in range(rv.num_outputs)]
        gc.collect()

        return rv

    def serialize(self, out_fd, upgrade_txn=False):
        # Ouput into a file.

        def wr(*a):
            self.write(out_fd, *a)

        out_fd.write(_MAGIC)

        if upgrade_txn and self.is_complete():
            # write out the ready-to-transmit txn
            # - means we are also a PSBT combiner in this case
            # - hard tho, due to variable length data.
            # - XXX probably a bad idea, so disabled for now
            out_fd.write(b'\x01\x00')       # keylength=1, key=b'', PSBT_GLOBAL_UNSIGNED_TX

            with SizerFile() as fd:
                self.finalize(fd)
                txn_len = fd.tell()

            out_fd.write(ser_compact_size(txn_len))
            self.finalize(out_fd)
        else:
            # provide original txn (unchanged)
            wr(PSBT_GLOBAL_UNSIGNED_TX, self.txn)

        if self.xpubs:
            for v, k in self.xpubs:
                wr(PSBT_GLOBAL_XPUB, v, k)

        if self.unknown:
            for k in self.unknown:
                wr(k[0], self.unknown[k], k[1:])

        # sep between globals and inputs
        out_fd.write(b'\0')

        for idx, inp in enumerate(self.inputs):
            inp.serialize(out_fd, idx)
            out_fd.write(b'\0')

        for idx, outp in enumerate(self.outputs):
            outp.serialize(out_fd, idx)
            out_fd.write(b'\0')

    def make_txn_sighash(self, replace_idx, replacement, sighash_type):
        # calculate the hash value for one input of current transaction
        # - blank all script inputs
        # - except one single tx in, which is provided
        # - serialize that without witness data
        # - append SIGHASH_ALL=1 value (LE32)
        # - sha256 over that
        fd = self.fd
        old_pos = fd.tell()
        rv = trezorcrypto.sha256()

        # version number
        rv.update(pack('<i', self.txn_version))           # nVersion

        # inputs
        rv.update(ser_compact_size(self.num_inputs))
        for in_idx, txi in self.input_iter():

            if in_idx == replace_idx:
                assert not self.inputs[in_idx].witness_utxo
                assert not self.inputs[in_idx].is_segwit
                assert replacement.scriptSig
                rv.update(replacement.serialize())
            else:
                txi.scriptSig = b''
                rv.update(txi.serialize())

        # outputs
        rv.update(ser_compact_size(self.num_outputs))
        for out_idx, txo in self.output_iter():
            rv.update(txo.serialize())

        # locktime
        rv.update(pack('<I', self.lock_time))

        assert sighash_type in VALID_SIGHASHES  # "only SIGHASH_ALL supported"
        # SIGHASH_ALL==1 value
        rv.update(b'\x01\x00\x00\x00')

        fd.seek(old_pos)

        # double SHA256
        return trezorcrypto.sha256(rv.digest()).digest()

    def make_txn_segwit_sighash(self, replace_idx, replacement, amount, scriptCode, sighash_type):
        # Implement BIP 143 hashing algo for signature of segwit programs.
        # see <https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki>
        #

        fd = self.fd
        old_pos = fd.tell()

        assert sighash_type == SIGHASH_ALL  # add support for others here

        if self.hashPrevouts is None:
            # First time thru, we'll need to hash up this stuff.

            po = trezorcrypto.sha256()
            sq = trezorcrypto.sha256()

            # input side
            for in_idx, txi in self.input_iter():
                po.update(txi.prevout.serialize())
                sq.update(pack("<I", txi.nSequence))

            self.hashPrevouts = trezorcrypto.sha256(po.digest()).digest()
            self.hashSequence = trezorcrypto.sha256(sq.digest()).digest()

            del po, sq, txi

            # output side
            ho = trezorcrypto.sha256()
            for out_idx, txo in self.output_iter():
                ho.update(txo.serialize())

            self.hashOutputs = trezorcrypto.sha256(ho.digest()).digest()

            del ho, txo
            gc.collect()

            # print('hPrev: %s' % str(b2a_hex(self.hashPrevouts), 'ascii'))
            # print('hSeq : %s' % str(b2a_hex(self.hashSequence), 'ascii'))
            # print('hOuts: %s' % str(b2a_hex(self.hashOutputs), 'ascii'))

        rv = trezorcrypto.sha256()

        # version number
        rv.update(pack('<i', self.txn_version))       # nVersion
        rv.update(self.hashPrevouts)
        rv.update(self.hashSequence)

        rv.update(replacement.prevout.serialize())

        # the "scriptCode" ... not well understood
        assert scriptCode, 'need scriptCode here'
        rv.update(scriptCode)

        rv.update(pack("<q", amount))
        rv.update(pack("<I", replacement.nSequence))

        rv.update(self.hashOutputs)

        # locktime, hashType
        rv.update(pack('<II', self.lock_time, sighash_type))

        fd.seek(old_pos)

        # double SHA256
        return trezorcrypto.sha256(rv.digest()).digest()

    def make_txn_taproot_sighash(self, input_idx, sighash_type, annex=None, ext_flag=0):
        # Implement BIP 341 hashing algo for signature of segwit programs.
        # see <https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki#signature-validation-rules>

        fd = self.fd
        old_pos = fd.tell()

        assert sighash_type == SIGHASH_DEFAULT

        if self.hashPrevouts is None:
            # First time thru, we'll need to hash up this stuff.

            prevouts = trezorcrypto.sha256()
            amounts = trezorcrypto.sha256()
            script_pubkeys = trezorcrypto.sha256()
            sequences = trezorcrypto.sha256()

            # input side
            for in_idx, txi in self.input_iter():
                utxo = self.inputs[in_idx].get_utxo(txi.prevout.n)
                prevouts.update(txi.prevout.serialize())
                amounts.update(pack("<q", utxo.nValue))
                script_pubkeys.update(ser_string(utxo.scriptPubKey))
                sequences.update(pack("<I", txi.nSequence))

            self.hashPrevouts = prevouts.digest()
            self.hashAmounts = amounts.digest()
            self.hashScriptPubkeys = script_pubkeys.digest()
            self.hashSequence = sequences.digest()

            del prevouts, amounts, script_pubkeys, sequences, txi

            # output side
            outputs = trezorcrypto.sha256()
            for out_idx, txo in self.output_iter():
                outputs.update(txo.serialize())

            self.hashOutputs = outputs.digest()

            del outputs, txo
            gc.collect()

        data = bytes([sighash_type])
        data += pack('<i', self.txn_version)
        data += pack('<I', self.lock_time)
        data += self.hashPrevouts
        data += self.hashAmounts
        data += self.hashScriptPubkeys
        data += self.hashSequence
        data += self.hashOutputs

        spend_type = (2 * ext_flag) + (1 if annex is not None else 0)
        data += pack('B', spend_type)

        data += pack('<I', input_idx)

        if annex is not None:
            data += trezorcrypto.sha256(ser_string(annex)).digest()

        # TODO: support bip342 script extensions:
        # see <https://github.com/bitcoin/bips/blob/master/bip-0342.mediawiki#common-signature-message-extension>

        fd.seek(old_pos)
        return tagged_hash('TapSighash', bytes([0]) + data)

    def is_complete(self):
        # Are all the inputs (now) signed?

        # some might have been given as signed
        signed = len(self.presigned_inputs)

        # plus we added some signatures
        for inp in self.inputs:
            if inp.is_multisig:
                # but we can't combine/finalize multisig stuff, so will never't be 'final'
                return False

            if inp.added_sig or inp.tap_key_sig:
                signed += 1

        return signed == self.num_inputs

    def finalize(self, fd):
        # Stream out the finalized transaction, with signatures applied
        # - assumption is it's complete already.
        # - returns the TXID of resulting transaction
        # - but in segwit case, needs to re-read to calculate it
        # - fd must be read/write and seekable to support txid calc

        fd.write(pack('<i', self.txn_version))           # nVersion

        # does this txn require witness data to be included?
        # - yes, if the original txn had some
        # - yes, if we did a segwit signature on any input
        needs_witness = self.had_witness or any(i.is_segwit for i in self.inputs if i)

        if needs_witness:
            # zero marker, and flags=0x01
            fd.write(b'\x00\x01')

        body_start = fd.tell()

        # inputs
        fd.write(ser_compact_size(self.num_inputs))
        for in_idx, txi in self.input_iter():
            inp = self.inputs[in_idx]

            if inp.is_segwit:

                if inp.is_p2sh:
                    # multisig (p2sh) segwit still requires the script here.
                    txi.scriptSig = ser_string(inp.scriptSig)
                else:
                    # major win for segwit (p2pkh): no redeem script bloat anymore
                    txi.scriptSig = b''

                # Actual signature will be in witness data area

            elif inp.added_sig:
                # insert the new signature(s)
                assert not inp.is_multisig, 'Multisig PSBT combine not supported'

                pubkey, der_sig = inp.added_sig

                s = b''
                s += ser_push_data(der_sig)
                s += ser_push_data(pubkey)

                txi.scriptSig = s

            fd.write(txi.serialize())

        # outputs
        fd.write(ser_compact_size(self.num_outputs))
        for out_idx, txo in self.output_iter():
            fd.write(txo.serialize())

            # print('self.outputs[{}].is_change: {}  self.outputs[{}].witness_script: {}'.format(
            #     out_idx, self.outputs[out_idx].is_change, out_idx, self.outputs[out_idx].witness_script))

            # capture change output amounts (if segwit)
            if self.outputs[out_idx].is_change and self.outputs[out_idx].witness_script:
                history.add_segwit_utxos(out_idx, txo.nValue)

        body_end = fd.tell()

        if needs_witness:
            # witness values
            # - preserve any given ones, add ours
            for in_idx, wit in self.input_witness_iter():
                inp = self.inputs[in_idx]

                if inp.is_segwit and (inp.added_sig or inp.tap_key_sig):
                    # put in new sig: wit is a CTxInWitness
                    assert not wit.scriptWitness.stack, 'replacing non-empty?'
                    assert not inp.is_multisig, 'Multisig PSBT combine not supported'

                    if inp.added_sig:
                        pubkey, der_sig = inp.added_sig
                        assert pubkey[0] in {0x02, 0x03} and len(pubkey) == 33, "bad v0 pubkey"
                        wit.scriptWitness.stack = [der_sig, pubkey]
                    else:
                        wit.scriptWitness.stack = [inp.tap_key_sig]

                fd.write(wit.serialize())

        # locktime
        fd.write(pack('<I', self.lock_time))

        # calc transaction ID
        if not needs_witness:
            # easy w/o witness data
            txid = trezorcrypto.sha256(fd.checksum.digest()).digest()
        else:
            # legacy cost here for segwit: re-read what we just wrote
            txid = calc_txid(fd, (0, fd.tell()), (body_start, body_end - body_start))

        # print('Calling add_segwit_utxos_finalize for txid:\n  {}'.format(txid))
        history.add_segwit_utxos_finalize(txid)

        return B2A(bytes(reversed(txid)))


# EOF
