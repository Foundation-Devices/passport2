# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validated, immutable instructions passed from policy matching to signing."""


class SpendPlan:
    __slots__ = ('policy_id', 'input_index', 'branch', 'address_index',
                 'script_context', 'owned_key_path', 'expected_pubkey',
                 'owned_key_paths', 'expected_pubkeys',
                 'sighash_type', 'script_pubkey', 'witness_script',
                 'timelocks', '_locked')

    def __init__(self, policy_id, input_index, branch, address_index,
                 script_context, owned_key_path, expected_pubkey,
                 sighash_type, script_pubkey=None, witness_script=None,
                 timelocks=(), owned_signing_keys=None):
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
