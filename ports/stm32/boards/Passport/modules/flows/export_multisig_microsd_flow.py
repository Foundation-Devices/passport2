# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_multisig_microsd_flow.py - Export a multisig wallet via microSD

from flows import SaveToMicroSDFlow


class ExportMultisigMicrosdFlow(SaveToMicroSDFlow):
    def __init__(self, context=None):
        from multisig_wallet import MultisigWallet
        from utils import get_folder_path
        from public_constants import DIR_MULTISIGS

        ms = MultisigWallet.get_by_idx(context)  # context is multisig index
        data = ms.to_file()
        filename = "{}-multisig.txt".format(ms.name)
        super().__init__(filename=filename,
                         path=get_folder_path(DIR_MULTISIGS),
                         data=data,
                         success_text="multisig config")
