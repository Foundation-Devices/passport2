# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_task.py - Run the main UI from startup based on device state


async def main_task():
    import common
    from flows import MainFlow
    import passport
    from uasyncio import sleep_ms

    # Check for terms, then start terms flow

    # Read system test flag from bootloader
    run_system_test = False
    if not passport.IS_SIMULATOR:
        import uctypes
        buf = uctypes.bytearray_at(0x38000000, 1)
        if buf[0] == 1:
            run_system_test = True

    # Run system test UI if asked by the bootloader
    if run_system_test:
        from system_test_ux import run_system_test_ux
        run_system_test_ux()
    else:

        # MainFlow handles setup, SCV, Login, then main UI
        num_cards = common.ui.create_single_card(MainFlow)

        # Start the first card_task
        common.ui.start_card_task(card_idx=num_cards - 1)

        await sleep_ms(100)
        common.system.enable_lv_refresh(True)
