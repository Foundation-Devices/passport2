# (c) Copyright 2020 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# exceptions.py - Exceptions defined by us.
#

# Caution: limited ability in Micropython to override system exceptions.


# PSBT / transaction related
class FatalPSBTIssue(RuntimeError):
    pass


CHANGE_ADDRESS_NOT_OURS = (
    "Transaction rejected. The change address doesn't belong to this wallet.")
CHANGE_MULTISIG_SETUP_MISMATCH = (
    "Transaction rejected. The change address doesn't match this multisig wallet's setup.")
CHANGE_WRONG_ACCOUNT_TYPE = (
    "Transaction rejected. The change address is the wrong type for this account.")


class FraudulentChangeOutput(FatalPSBTIssue):
    def __init__(self, out_idx, msg):
        self.out_idx = out_idx
        super().__init__(msg)


class IncorrectUTXOAmount(FatalPSBTIssue):
    def __init__(self, in_idx, msg):
        super().__init__('Input #%d: %s' % (in_idx, msg))


class MultisigOutOfSpace(RuntimeError):
    pass


# EOF
