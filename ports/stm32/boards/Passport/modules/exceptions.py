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


class FraudulentChangeOutput(FatalPSBTIssue):
    def __init__(self, out_idx, msg):
        super().__init__('Output #%d: %s' % (out_idx, msg))


class IncorrectUTXOAmount(FatalPSBTIssue):
    def __init__(self, in_idx, msg):
        super().__init__('Input #%d: %s' % (in_idx, msg))


class MultisigOutOfSpace(RuntimeError):
    pass


# EOF
