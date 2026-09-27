# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from ubinascii import unhexlify

from data_codecs.qr_type import QRType
from wallets.blockstream import BlockstreamWallet, create_blockstream_account_cbor
from wallets.sw_wallets import supported_software_wallets


public_key = unhexlify('02' + '11' * 32)
chain_code = unhexlify('22' * 32)

cbor = create_blockstream_account_cbor(public_key,
                                       chain_code,
                                       0x12345678,
                                       7,
                                       0x90abcdef,
                                       False)
expected = unhexlify(
    'a2'
    '011a12345678'
    '0281d90134d90194d9012f'
    'a4'
    '035821' + '02' + '11' * 32 +
    '045820' + '22' * 32 +
    '06d90130a3'
    '01861854f500f507f5'
    '021a12345678'
    '0303'
    '081a90abcdef')
# This pins the tags, field order, and canonical CBOR encodings Jade accepts.
assert cbor == expected

testnet_cbor = create_blockstream_account_cbor(public_key,
                                               chain_code,
                                               0x12345678,
                                               24,
                                               0x90abcdef,
                                               True)
assert testnet_cbor[0] == 0xa2
assert b'\x05\xd9\x01\x31\xa2\x01\x00\x02\x01' in testnet_cbor
assert b'\x01\x86\x18\x54\xf5\x01\xf5\x18\x18\xf5' in testnet_cbor

assert BlockstreamWallet in supported_software_wallets
assert BlockstreamWallet['label'] == 'Blockstream'
assert len(BlockstreamWallet['sig_types']) == 1

sig_type = BlockstreamWallet['sig_types'][0]
assert sig_type['id'] == 'single-sig'

export_modes = BlockstreamWallet['export_modes']
assert len(export_modes) == 1
assert export_modes[0]['id'] == 'qr'
assert export_modes[0]['qr_type'] == QRType.UR2

return_value.write(b'OK')
