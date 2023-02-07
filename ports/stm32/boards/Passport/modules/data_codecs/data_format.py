# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# data_format.py
#
# Simple types to act as an enums for all data formats that we read from file or QR code
#

from .multisig_config_sampler import MultisigConfigSampler
from .psbt_txn_sampler import PsbtTxnSampler
from .seed_sampler import SeedSampler
from .address_sampler import AddressSampler

from flows import (
    MagicScanSignPsbtFlow,
    MagicScanImportMultisigFlow,
    MagicScanImportSeedFlow,
    MagicScanValidateAddressFlow)


samplers = [
    {'name': 'psbt', 'sampler': PsbtTxnSampler, 'flow': MagicScanSignPsbtFlow},
    {'name': 'multisig', 'sampler': MultisigConfigSampler, 'flow': MagicScanImportMultisigFlow},
    {'name': 'seed', 'sampler': SeedSampler, 'flow': MagicScanImportSeedFlow},
    {'name': 'address', 'sampler': AddressSampler, 'flow': MagicScanValidateAddressFlow},
]


def get_flow_for_data(data, flow_name=None):
    for entry in samplers:
        if (flow_name is None or flow_name == entry['name']) and entry['sampler'].sample(data) is True:
            return entry['flow']
    return None
