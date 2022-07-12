# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# import_multisig_config_task.py - Task to import a multisig config

# from utils import show_top_menu, problem_file_line
# from auth import maybe_enroll_xpub

# TODO: The auth code this calls might be a lot of work to adapt as it mixed UI with functionality


async def import_multisig_config_task(on_done, data):
    pass
    # try:
    #     maybe_enroll_xpub(config=data)
    #     await show_top_menu()

    #     return not common.is_new_wallet_a_duplicate

    # except Exception as e:
    #     await ux_show_story('Invalid multisig configuration data.\n\n{}\n{}'.format(e, problem_file_line(e)),
    #                         title='Error')
    #     return False
