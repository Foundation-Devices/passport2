# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# __init__.py

from .flow import *

# Base Flows
from .page_flow import *
from .menu_flow import *
from .main_flow import *
from .login_flow import *
from .save_to_microsd_flow import *
from .scan_qr_flow import *
from .backup_common_flow import *
from .seed_warning_flow import *
from .series_of_pages_flow import *

# QR Magic Scan flows
from .magic_scan_import_multisig_flow import *
from .magic_scan_import_seed_flow import *
from .magic_scan_sign_psbt_flow import *
from .magic_scan_validate_address_flow import *
from .magic_scan_flow import *

from .about_flow import *
from .address_explorer_flow import *
from .apply_passphrase_flow import *
from .auto_backup_flow import *
from .backup_flow import *
from .casa_health_check_common_flow import *
from .casa_health_check_microsd_flow import *
from .casa_health_check_qr_flow import *
from .change_pin_flow import *
from .delete_account_flow import *
from .delete_multisig_flow import *
from .erase_passport_flow import *
from .export_derived_key_flow import *
from .export_multisig_microsd_flow import *
from .export_multisig_qr_flow import *
from .export_summary_flow import *
from .selected_file_flow import *
from .file_picker_flow import *
from .format_microsd_flow import *
from .get_seed_words_flow import *
from .import_multisig_wallet_flow import *
from .import_multisig_wallet_from_microsd_flow import *
from .import_multisig_wallet_from_qr_flow import *
from .install_dev_pubkey_flow import *
from .list_files_flow import *
from .new_account_flow import *
from .new_derived_key_flow import *
from .new_seed_flow import *
from .connect_wallet_flow import *
from .read_file_flow import *
from .remove_dev_pubkey_flow import *
from .rename_account_flow import *
from .rename_derived_key_flow import *
from .rename_device_flow import *
from .rename_multisig_flow import *
from .reset_pin_flow import *
from .restore_backup_flow import *
from .restore_seed_flow import *
from .scv_flow import *
from .set_chain_flow import *
from .set_initial_pin_flow import *
from .show_security_words_setting_flow import *
from .sign_electrum_message_flow import *
from .sign_text_file_flow import *
from .sign_psbt_common_flow import *
from .sign_psbt_microsd_flow import *
from .sign_psbt_qr_flow import *
from .system_test_camera_flow import *
from .system_test_microsd_flow import *
from .system_test_flow import *
from .terms_of_use_flow import *
from .update_firmware_flow import *
from .verify_address_flow import *
from .verify_backup_flow import *
from .view_backup_code_flow import *
from .view_current_firmware_flow import *
from .view_derived_key_details_flow import *
from .view_dev_pubkey_flow import *
from .view_multisig_details_flow import *
from .view_seed_words_flow import *

# Top-level flows need to be declared after other flows that they use

from .initial_seed_setup_flow import *
from .envoy_setup_flow import *
from .manual_setup_flow import *
from .select_setup_mode_flow import *
