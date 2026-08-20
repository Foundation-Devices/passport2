# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from ubinascii import unhexlify

from data_codecs.multisig_config_sampler import MultisigConfigSampler
from data_codecs.qr_type import QRType
from wallets.multisig_import import read_multisig_config_from_microsd, read_multisig_config_from_qr
from wallets.sw_wallets import supported_software_wallets
from wallets.unchained import UnchainedWallet, create_unchained_hdkey_cbor


public_key = unhexlify('02' + '11' * 32)
chain_code = unhexlify('22' * 32)
fingerprint = 0xf23f9fd2

cbor = create_unchained_hdkey_cbor(public_key,
                                   chain_code,
                                   fingerprint,
                                   fingerprint,
                                   False)
expected = unhexlify(
    'a5'
    '035821' + '02' + '11' * 32 +
    '045820' + '22' * 32 +
    '05d90131a0'
    '06d90130a3'
    '0182182df5'
    '021af23f9fd2'
    '0301'
    '081af23f9fd2')
assert cbor == expected

testnet_cbor = create_unchained_hdkey_cbor(public_key, chain_code, 0, 0, True)
assert testnet_cbor[0] == 0xa4
assert b'\x05\xd9\x01\x31\xa1\x02\x01' in testnet_cbor
assert b'\x06\xd9\x01\x30\xa2\x01\x82\x18\x2d\xf5\x03\x01' in testnet_cbor

assert UnchainedWallet in supported_software_wallets
assert UnchainedWallet['label'] == 'Unchained'
assert len(UnchainedWallet['sig_types']) == 1

sig_type = UnchainedWallet['sig_types'][0]
assert sig_type['id'] == 'multisig'
assert sig_type['import_qr'] is read_multisig_config_from_qr
assert sig_type['import_microsd'] is read_multisig_config_from_microsd

export_modes = UnchainedWallet['export_modes']
assert export_modes[0]['id'] == 'qr'
assert export_modes[0]['qr_type'] == QRType.UR2
assert export_modes[1]['id'] == 'microsd'
assert export_modes[1]['filename_pattern_multisig'] == '{xfp}-unchained-multisig.json'

unchained_config = b'''# Coldcard Multisig setup file (exported from @caravan/wallets)
Name: example-vault
Policy: 2 of 3
Derivation: m/48'/0'/0'/2'
Format: P2WSH
'''
assert MultisigConfigSampler.sample(unchained_config)

return_value.write(b'OK')
