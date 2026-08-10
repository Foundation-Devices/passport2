# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""WalletPolicy adapter for Passport's existing MultisigWallet records."""

from policy_errors import PolicyMismatchError
from wallet_policy import DerivedPolicyOutput


def _sha256(data):
    try:
        import trezorcrypto
        return trezorcrypto.sha256(data).digest()
    except ImportError:  # pragma: no cover - CPython host tests
        import hashlib
        return hashlib.sha256(data).digest()


def _hash160(data):
    try:
        import trezorcrypto
        first = trezorcrypto.sha256(data).digest()
        return trezorcrypto.ripemd160(first).digest()
    except ImportError:  # pragma: no cover - CPython host tests
        import hashlib
        first = hashlib.sha256(data).digest()
        return hashlib.new('ripemd160', first).digest()


class StandardMultisigPolicy:
    """Expose legacy M-of-N records through the wallet-policy derivation API."""

    __slots__ = ('wallet', 'name', 'network', 'policy_id', 'kind')

    def __init__(self, wallet):
        self.wallet = wallet
        self.name = wallet.name
        self.network = wallet.chain_type
        self.policy_id = 'legacy-multisig:{}'.format(wallet.id)
        self.kind = 'standard_multisig'

    def derive(self, branch, index, chain=None, key_resolver=None):
        if branch not in (0, 1):
            raise ValueError('branch must be receive (0) or change (1)')
        chain = chain or self.wallet.chain
        if getattr(chain, 'ctype', None) != self.network:
            raise PolicyMismatchError('Multisig network does not match the active network')
        derived_index, _, address, script = next(
            self.wallet.yield_addresses(index, 1, change_idx=branch))
        if derived_index != index:
            raise PolicyMismatchError('Multisig address derivation returned the wrong index')

        from public_constants import AF_P2SH, AF_P2WSH, AF_P2WSH_P2SH
        address_format = self.wallet.addr_fmt
        if address_format == AF_P2WSH:
            witness_script = script
            redeem_script = None
            script_pubkey = b'\x00\x20' + _sha256(script)
        elif address_format == AF_P2WSH_P2SH:
            witness_script = script
            redeem_script = b'\x00\x20' + _sha256(script)
            script_pubkey = b'\xa9\x14' + _hash160(redeem_script) + b'\x87'
        elif address_format == AF_P2SH:
            witness_script = None
            redeem_script = script
            script_pubkey = b'\xa9\x14' + _hash160(script) + b'\x87'
        else:
            raise PolicyMismatchError('Unsupported legacy multisig address format')
        return DerivedPolicyOutput(self.policy_id, branch, index, witness_script,
                                   script_pubkey, address, redeem_script)

    def match_scripts(self, branch, index, utxo_script_pubkey,
                      witness_script=None, redeem_script=None, chain=None):
        derived = self.derive(branch, index, chain)
        if bytes(utxo_script_pubkey) != derived.script_pubkey:
            raise PolicyMismatchError('UTXO script does not match the registered multisig wallet')
        if witness_script is not None and bytes(witness_script) != derived.witness_script:
            raise PolicyMismatchError('Witness script does not match the registered multisig wallet')
        if redeem_script is not None and bytes(redeem_script) != derived.redeem_script:
            raise PolicyMismatchError('Redeem script does not match the registered multisig wallet')
        return derived
