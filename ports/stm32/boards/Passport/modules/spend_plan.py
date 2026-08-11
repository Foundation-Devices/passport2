# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validated, immutable instructions passed from policy matching to signing."""


class SpendPlan:
    __slots__ = ('policy_id', 'input_index', 'branch', 'address_index',
                 'script_context', 'owned_key_path', 'expected_pubkey',
                 'owned_key_paths', 'expected_pubkeys',
                 'sighash_type', 'script_pubkey', 'witness_script', 'tapleaf_script',
                 'tapleaf_hash', 'control_block', 'internal_key', 'merkle_root',
                 'timelocks', '_locked')

    def __init__(self, policy_id, input_index, branch, address_index,
                 script_context, owned_key_path, expected_pubkey,
                 sighash_type, script_pubkey=None, witness_script=None, tapleaf_script=None,
                 tapleaf_hash=None, control_block=None, internal_key=None,
                 merkle_root=None, timelocks=(), owned_signing_keys=None):
        object.__setattr__(self, '_locked', False)
        self.policy_id = policy_id
        self.input_index = input_index
        self.branch = branch
        self.address_index = address_index
        self.script_context = script_context
        self.owned_key_path = tuple(owned_key_path)
        self.expected_pubkey = bytes(expected_pubkey)
        if owned_signing_keys is None:
            signing_keys = ((self.owned_key_path, self.expected_pubkey),)
        else:
            signing_keys = tuple((tuple(path), bytes(pubkey))
                                 for path, pubkey in owned_signing_keys)
            if not signing_keys or signing_keys[0] != (
                    self.owned_key_path, self.expected_pubkey):
                raise ValueError('Primary signing key must match the spend plan')
        self.owned_key_paths = tuple(path for path, _ in signing_keys)
        self.expected_pubkeys = tuple(pubkey for _, pubkey in signing_keys)
        if len(set(self.expected_pubkeys)) != len(self.expected_pubkeys):
            raise ValueError('Spend plan signing keys must be distinct')
        self.sighash_type = sighash_type
        self.script_pubkey = bytes(script_pubkey) if script_pubkey is not None else None
        self.witness_script = bytes(witness_script) if witness_script is not None else None
        self.tapleaf_script = bytes(tapleaf_script) if tapleaf_script is not None else None
        self.tapleaf_hash = bytes(tapleaf_hash) if tapleaf_hash is not None else None
        self.control_block = bytes(control_block) if control_block is not None else None
        self.internal_key = bytes(internal_key) if internal_key is not None else None
        self.merkle_root = bytes(merkle_root) if merkle_root is not None else None
        self.timelocks = tuple(timelocks)
        object.__setattr__(self, '_locked', True)

    def __setattr__(self, name, value):
        if getattr(self, '_locked', False):
            raise AttributeError('SpendPlan is immutable')
        object.__setattr__(self, name, value)

    def assert_p2wsh_scope(self, input_index, subpaths, script_pubkey,
                           witness_script, sighash_type, required_keys,
                           existing_signatures=()):
        """Revalidate the security boundary immediately before signing."""
        if self.script_context != 'p2wsh' or input_index != self.input_index:
            raise ValueError('Wallet policy spend plan is for another input')
        if sighash_type != self.sighash_type:
            raise ValueError('Wallet policy sighash changed after validation')
        if bytes(script_pubkey) != self.script_pubkey:
            raise ValueError('Wallet policy UTXO changed after validation')
        if bytes(witness_script) != self.witness_script:
            raise ValueError('Wallet policy witness script changed after validation')
        expected_required = set(self.expected_pubkeys) - set(existing_signatures)
        if set(required_keys) != expected_required:
            raise ValueError('Wallet policy signing key changed after validation')
        for path, pubkey in zip(self.owned_key_paths, self.expected_pubkeys):
            if pubkey not in subpaths:
                raise ValueError('Wallet policy signing derivation is missing')
            if tuple(subpaths[pubkey]) != path:
                raise ValueError('Wallet policy signing derivation changed after validation')
        return True

    def assert_tapscript_scope(self, input_index, tap_subpaths,
                               script_pubkey, tap_leaf_scripts,
                               tap_internal_key, tap_merkle_root,
                               sighash_type, required_key):
        """Revalidate every BIP371 field immediately before Schnorr signing."""
        if self.script_context != 'tapscript' or input_index != self.input_index:
            raise ValueError('Wallet policy spend plan is for another input')
        if sighash_type != self.sighash_type:
            raise ValueError('Wallet policy sighash changed after validation')
        if bytes(script_pubkey) != self.script_pubkey:
            raise ValueError('Wallet policy UTXO changed after validation')
        if required_key != self.expected_pubkey:
            raise ValueError('Wallet policy signing key changed after validation')
        if self.expected_pubkey not in tap_subpaths:
            raise ValueError('Wallet policy Taproot derivation is missing')
        path, leaf_hashes = tap_subpaths[self.expected_pubkey]
        if tuple(path) != self.owned_key_path or set(leaf_hashes) != {self.tapleaf_hash}:
            raise ValueError('Wallet policy Taproot derivation changed after validation')
        if len(tap_leaf_scripts) != 1 or \
                tap_leaf_scripts.get(self.control_block) != self.tapleaf_script + b'\xc0':
            raise ValueError('Wallet policy Taproot leaf or control block changed after validation')
        if tap_internal_key is not None and bytes(tap_internal_key) != self.internal_key:
            raise ValueError('Wallet policy Taproot internal key changed after validation')
        if tap_merkle_root is not None and bytes(tap_merkle_root) != self.merkle_root:
            raise ValueError('Wallet policy Taproot merkle root changed after validation')
        return True
