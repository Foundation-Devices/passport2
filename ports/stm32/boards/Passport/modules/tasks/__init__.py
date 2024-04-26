# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import passport

if passport.HAS_FUEL_GAUGE:
    from .fuelgauge_task import fuelgauge_task
else:
    from .battery_adc_task import battery_adc_task

from .apply_passphrase_task import apply_passphrase_task
from .auto_shutdown_task import auto_shutdown_task
from .bip85_seed_task import *
from .calculate_file_sha256_task import calculate_file_sha256_task
from .card_task import card_task
from .change_pin_task import change_pin_task
from .charge_monitor_task import charge_monitor_task
from .copy_firmware_to_spi_flash_task import copy_firmware_to_spi_flash_task
from .copy_psbt_file_to_external_flash_task import copy_psbt_file_to_external_flash_task
from .copy_psbt_to_external_flash_task import copy_psbt_to_external_flash_task
from .clear_psbt_from_external_flash_task import clear_psbt_from_external_flash_task
from .create_wallet_export_task import create_wallet_export_task
from .custom_microsd_write_task import custom_microsd_write_task
from .delete_account_task import delete_account_task
from .delay_task import delay_task
from .delete_multisig_task import delete_multisig_task
from .double_check_psbt_change_task import double_check_psbt_change_task
from .erase_passport_task import erase_passport_task
from .format_microsd_task import format_microsd_task
from .generate_addresses_task import generate_addresses_task
from .get_security_words_task import get_security_words_task
from .get_seed_words_task import get_seed_words_task
from .get_backup_code_task import get_backup_code_task
from .login_task import login_task
from .lvgl_task import lvgl_task
from .main_task import main_task
from .make_microsd_file_system_task import make_microsd_file_system_task
from .new_seed_task import new_seed_task
from .nostr_key_task import nostr_key_task
from .power_button_task import power_button_task
from .read_file_task import read_file_task
from .rename_account_task import rename_account_task
from .rename_derived_key_task import rename_derived_key_task
from .rename_multisig_task import rename_multisig_task
from .restore_backup_task import restore_backup_task
from .save_multisig_wallet_task import save_multisig_wallet_task
from .save_new_account_task import save_new_account_task
from .save_new_derived_key_task import save_new_derived_key_task
from .save_seed_task import save_seed_task
from .search_for_address_task import search_for_address_task
from .set_initial_pin_task import set_initial_pin_task
from .sign_psbt_task import sign_psbt_task
from .sign_text_file_task import sign_text_file_task
from .validate_electrum_message_task import validate_electrum_message_task
from .validate_psbt_task import validate_psbt_task
from .verify_firmware_signature_task import verify_firmware_signature_task
from .verify_backup_task import verify_backup_task
