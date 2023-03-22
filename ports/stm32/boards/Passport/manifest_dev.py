# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Keep lists below sorted for easier reference

freeze('$(MPY_DIR)/ports/stm32/boards/Passport/modules',
       ('developer/__init__.py',
        'developer/battery_page.py',
        'developer/delete_derived_keys_flow.py',
        'developer/developer_functions_flow.py',
        'developer/spin_delay_flow.py',
        ))

include("$(MPY_DIR)/ports/stm32/boards/Passport/manifest.py")
