# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2020 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2020 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# history.py - store some history about past transactions and/or outputs they involved
#
import trezorcrypto
import gc
import chains
from utils import B2A
from ustruct import pack, unpack
from exceptions import IncorrectUTXOAmount
from ubinascii import b2a_base64, a2b_base64
from serializations import COutPoint, uint256_from_bytes
from common import flash_cache

# Limited space in external flash, so we compress as much as possible:
# - would be bad for privacy to store these **UTXO amounts** in plaintext
# - result is stored in a JSON serialization, so needs to be text encoded
# - using base64, in two parts, concatenated
#       - 15 bytes are hash over txnhash:out_num => base64 => 20 chars text
#       - 8 bytes exact satoshi value => base64 (pad trimmed) => 11 chars
# - stored satoshi value is XOR'ed with LSB from prevout txn hash, which isn't stored
# - result is a 31 character string for each history entry, plus 4 overhead => 35 each
#

# We have 8K of space per slot (and 16 slots in Gen 1.2)
# Each entry is 35 bytes, so we can hold 234 entries.
_HISTORY_MAX_MEM = const(234)

# length of hashed & encoded key only (base64(15 bytes) => 20)
_ENCKEY_LEN = const(20)

# length of a whole entry: key, then the value (base64(8 bytes) without padding => 11)
_ENTRY_LEN = const(31)

# Entries per chunk of _Entries' storage (806 bytes); 9 chunks hold them all.
_ENTRIES_PER_CHUNK = const(26)


class _Entries:
    # The cache's entries, oldest first, as the same text that is saved, in chunks
    # made once. Kept as strings, every entry added after a large transaction would
    # be a small object left wherever the heap had room at that moment, and a few
    # hundred of those split the free memory into pieces too small for the next one.
    def __init__(self):
        self.chunks = [bytearray(_ENTRY_LEN * _ENTRIES_PER_CHUNK)
                       for _ in range((_HISTORY_MAX_MEM + _ENTRIES_PER_CHUNK - 1) // _ENTRIES_PER_CHUNK)]
        # Entries go in order until the storage is full; after that each new one
        # replaces the oldest, which is at `first`.
        self.first = 0
        self.count = 0

    def __len__(self):
        return self.count

    def _slot(self, pos):
        return self.chunks[pos // _ENTRIES_PER_CHUNK], (pos % _ENTRIES_PER_CHUNK) * _ENTRY_LEN

    def append(self, entry):
        # The entry is written before the ring moves on, so one that can't be written
        # leaves the others and their order as they were.
        if len(entry) != _ENTRY_LEN:
            raise ValueError('History entry of %d bytes' % len(entry))
        full = self.count == _HISTORY_MAX_MEM
        pos = self.first if full else self.count
        chunk, off = self._slot(pos)
        chunk[off:off + _ENTRY_LEN] = entry
        if full:
            self.first = (pos + 1) % _HISTORY_MAX_MEM
        else:
            self.count = pos + 1

    def find(self, key):
        # The value text stored with key (the encoded key, as bytes), or None. A miss
        # allocates nothing, so the lookups for a PSBT's inputs leave no garbage.
        left = self.count
        for chunk in self.chunks:
            if left <= 0:
                break
            end = min(left, _ENTRIES_PER_CHUNK) * _ENTRY_LEN
            left -= _ENTRIES_PER_CHUNK
            for off in range(0, end, _ENTRY_LEN):
                i = 0
                while i < _ENCKEY_LEN and chunk[off + i] == key[i]:
                    i += 1
                if i == _ENCKEY_LEN:
                    return bytes(chunk[off + _ENCKEY_LEN:off + _ENTRY_LEN])
        return None

    def clear(self):
        self.first = 0
        self.count = 0

    def json_items(self):
        # As saved in the flash cache: a list of strings, oldest first.
        for i in range(self.count):
            chunk, off = self._slot((self.first + i) % _HISTORY_MAX_MEM)
            yield bytes(chunk[off:off + _ENTRY_LEN]).decode()


class OutptValueCache:
    # storing a list in flash_cache
    # - maps from hash of txid:n to expected sats there
    # - stored as b64 key concatenated w/ int
    KEY = 'ovc'

    # we keep extra entries here during the current power-up
    # as defense against using very large txn in the attack
    entries = None

    @classmethod
    def clear(cls):
        # Without loading the history first: with little memory left, loading could
        # fail before the saved copy is removed.
        if cls.entries is not None:
            cls.entries.clear()
        flash_cache.remove(cls.KEY)
        flash_cache.save()

    @classmethod
    def load_cache(cls):
        # first time: read saved value, but rest of time; use what's in memory
        if cls.entries is None:
            entries = _Entries()
            saved = flash_cache.get(cls.KEY)
            if isinstance(saved, list):
                # By index: a slice would be one more copy of the list.
                for i in range(max(0, len(saved) - _HISTORY_MAX_MEM), len(saved)):
                    entry = saved[i]
                    if isinstance(entry, str):
                        entry = entry.encode()
                        if len(entry) == _ENTRY_LEN:
                            entries.append(entry)
                # The loaded list would otherwise stay in memory beside the entries.
                # They save as the same list, less any entry skipped above, so there
                # is nothing to write yet.
                flash_cache.replace(cls.KEY, entries)
            cls.entries = entries

    @classmethod
    def _key(cls, prevout):
        # hash up the txid and output number, truncate, and encode as base64
        # - truncating at (mod3) bytes so no padding on b64 output
        # - expects a COutPoint
        md = trezorcrypto.sha256('OutputValueCache')
        md.update(prevout.serialize())
        return b2a_base64(md.digest()[:15])[:-1]

    @classmethod
    def encode_value(cls, prevout, amt):
        # XOR stored value with 64 LSB of original txnhash
        xor = pack('<Q', prevout.hash & ((1 << 64) - 1))
        val = bytes(i ^ j for i, j in zip(xor, pack('<Q', amt)))
        assert len(val) == 8
        return b2a_base64(val)[:-2].decode()

    @classmethod
    def decode_value(cls, prevout, text):
        # base64 decode, xor w/ hash, decode as uint64
        if isinstance(text, str):
            text = text.encode()
        xor = pack('<Q', prevout.hash & ((1 << 64) - 1))
        val = a2b_base64(text + b'=')
        assert len(val) == 8
        val = bytes(i ^ j for i, j in zip(xor, val))
        return unpack('<Q', val)[0]

    @classmethod
    def fetch_amount(cls, prevout):
        # Return the amount we expect for this utxo, if we have it, else None
        cls.load_cache()

        if not cls.entries:
            return None

        value = cls.entries.find(cls._key(prevout))
        if value is None:
            return None
        return cls.decode_value(prevout, value)

    @classmethod
    def verify_amount(cls, prevout, amount, in_idx):
        # Check previously recorded amounts without trusting new PSBT data.
        # New amounts are recorded only after successful signing. Deliberately
        # forget amounts seen only in unsigned/rejected PSBTs: remembering them
        # lets an untrusted coordinator poison later legitimate spends. This
        # loses cross-attempt comparison until we sign; history remains a
        # secondary check, not a replacement for non_witness_utxo verification.
        # raises IncorrectUTXOAmount with details if it fails, which should abort any signing
        exp = cls.fetch_amount(prevout)

        if exp is not None and exp != amount:
            # Found the hacking we are looking for!
            ch = chains.current_chain()
            exp, units = ch.render_value(exp, True)
            amount, _ = ch.render_value(amount, True)

            raise IncorrectUTXOAmount(in_idx, "Expected %s but PSBT claims %s %s" % (
                exp, amount, units))
        return exp

    @classmethod
    def record_amount(cls, prevout, amount, in_idx):
        # Only call for inputs whose ownership was verified and which we signed.
        if cls.verify_amount(prevout, amount, in_idx) is None:
            cls.add(prevout, amount)

    @classmethod
    def record_amounts(cls, entries):
        # record_amount() for each (prevout, amount, in_idx), updating the saved copy
        # once at the end rather than after every input.
        cls.load_cache()
        added = False
        try:
            for prevout, amount, in_idx in entries:
                if cls.verify_amount(prevout, amount, in_idx) is None:
                    cls.add(prevout, amount, save=False)
                    added = True
        finally:
            if added:
                flash_cache.set(cls.KEY, cls.entries)

    @classmethod
    def add(cls, prevout, amount, save=True):
        # protect privacy, compress a little, and save it.
        # - we know it's not yet in our lists
        key = cls._key(prevout)
        # print('add to cache: prevout={} amount={}'.format(prevout, amount))

        # Holds the newest _HISTORY_MAX_MEM entries, all of which are saved.
        cls.load_cache()

        # save new addition
        assert len(key) == _ENCKEY_LEN
        assert amount > 0
        cls.entries.append(key + cls.encode_value(prevout, amount).encode())

        # update what we're going to save long-term
        if save:
            flash_cache.set(cls.KEY, cls.entries)


# As we build a new transaction, track what we need to capture
new_outpts = []


def add_segwit_utxos(out_idx, amount):
    # After signing and finalization, we would know all change outpoints
    # (but not the txid yet)
    global new_outpts
    new_outpts.append((out_idx, amount))


def add_segwit_utxos_finalize(txid):
    # Once we know the final txid, assume this txn will be broadcast, mined,
    # and capture the future UTXO outputs it will represent at that point.
    global new_outpts

    # might not have any change, or they may not be segwit
    if not new_outpts:
        # print('No new outputs!')
        return

    # add it to the cache
    prevout = COutPoint(uint256_from_bytes(txid), 0)
    for oi, amount in new_outpts:
        prevout.n = oi
        OutptValueCache.add(prevout, amount)

    new_outpts.clear()


def load():
    # Loading the history allocates its storage, so do it before a PSBT is read, while
    # the heap is still in one piece. Left to the first input checked, it comes when
    # the inputs' work has broken the free memory into small pieces.
    OutptValueCache.load_cache()


# shortcut
def verify_amount(*a):
    OutptValueCache.verify_amount(*a)


# EOF
