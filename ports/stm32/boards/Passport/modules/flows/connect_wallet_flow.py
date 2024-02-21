# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# connect_wallet_flow.py - Connect a new software wallet with Passport.

import lvgl as lv
from flows import Flow, ImportMultisigWalletFlow
from pages import (
    AddressTypeChooserPage,
    ExportModeChooserPage,
    ErrorPage,
    InfoPage,
    InsertMicroSDPage,
    QuestionPage,
    ShowQRPage,
    SigTypeChooserPage,
    SuccessPage,
    SWWalletChooserPage)
from tasks import (
    create_wallet_export_task,
    generate_addresses_task)
from wallets.utils import (
    get_deriv_path_from_address_and_acct,
    get_addr_type_from_address,
    get_deriv_path_from_addr_type_and_acct,
    get_addr_type_from_deriv,
    derive_address)
from public_constants import TRUST_PSBT
from wallets.constants import EXPORT_MODE_MICROSD, EXPORT_MODE_QR
from wallets.sw_wallets import supported_software_wallets
from utils import random_hex, spinner_task
from foundation import ur
import common
import microns
import foundation
from errors import Error


def find_wallet_by_label(label, default_value):
    for _, entry in enumerate(supported_software_wallets):
        if entry.get('label') == label:
            return entry

    return default_value


def find_sig_type_by_id(sw_wallet, id, default_value):
    if not sw_wallet:
        return default_value

    for entry in sw_wallet.get('sig_types', []):
        if entry.get('id') == id:
            return entry

    return default_value


def find_export_mode_by_id(sw_wallet, id, default_value):
    if not sw_wallet:
        return default_value

    for entry in sw_wallet.get('export_modes', []):
        if entry.get('id') == id:
            return entry

    return default_value


def get_addresses_in_range(start, end, addr_type, acct_num, ms_wallet):
    # print('addr_type={} acct_num={} ms_wallet={}'.format(addr_type, acct_num, ms_wallet))

    entries = []
    for i in range(start, end):
        fmt = get_deriv_path_from_addr_type_and_acct(addr_type, acct_num, ms_wallet is not None)
        deriv_path = fmt.format(acct_num)
        entry = derive_address(deriv_path, i, addr_type, ms_wallet)
        entries.append(entry)
    return entries


class ConnectWalletFlow(Flow):
    def __init__(self, sw_wallet=None, statusbar=None):
        self.sw_wallet = find_wallet_by_label(sw_wallet, None)
        if self.sw_wallet is not None:
            start_state = self.choose_sig_type
        else:
            start_state = self.choose_sw_wallet

        super().__init__(initial_state=start_state, name='ConnectWalletFlow', statusbar=statusbar)

        self.acct_num = common.ui.get_active_account().get('acct_num')
        self.sig_type = None
        self.export_mode = None
        self.acct_info = None
        self.verified = False
        self.deriv_path = None   # m/84'/0'/123'  Used to derive the HDNode
        self.multisig_wallet = None
        self.exported = False
        self.next_addr = 0
        self.addr_type = None
        self.progress_made = False
        self.error = None

        # We will use the defaults above for anything not restored below
        self.restore()

    def __repr__(self):
        return """ConnectWalletFlow: sw_wallet={}, sig_type={}, export_mode={},
  acct_info={}, acct_num={}, verified={},
  deriv_path={}, addr_type={}, multisig_wallet={},
  exported={}, next_addr={}""".format(
            self.sw_wallet,
            self.sig_type,
            self.export_mode,
            self.acct_info,
            self.acct_num,
            self.verified,
            self.deriv_path,
            self.addr_type,
            self.multisig_wallet,
            self.exported,
            self.next_addr)

    def get_save_data(self):
        data = super().get_save_data()

        connect_wallet_data = {
            'sw_wallet': self.sw_wallet['label'] if self.sw_wallet else None,
            'sig_type': self.sig_type['id'] if self.sig_type else None,
            'export_mode': self.export_mode['id'] if self.export_mode else None,
            'acct_info': self.acct_info,
            'acct_num': self.acct_num,
            'deriv_path': self.deriv_path,
            'verified': self.verified,
            'multisig_id': self.multisig_wallet.id if self.multisig_wallet else None,
            'exported': self.exported,
            'next_addr': self.next_addr,
            'addr_type': self.addr_type,
        }

        # print('save connect_wallet_data={}'.format(connect_wallet_data))

        data.update(connect_wallet_data)

        # print('save data={}'.format(data))

        return data

    def restore_items(self, data):
        from multisig_wallet import MultisigWallet

        super().restore_items(data)

        self.sw_wallet = find_wallet_by_label(data.get('sw_wallet'), None)
        self.sig_type = find_sig_type_by_id(self.sw_wallet, data.get('sig_type'), None)
        self.export_mode = find_export_mode_by_id(self.sw_wallet, data.get('export_mode'), None)
        self.acct_info = data.get('acct_info')
        self.acct_num = data.get('acct_num')
        self.verified = data.get('verified', False)
        self.deriv_path = data.get('deriv_path')
        self.multisig_wallet = MultisigWallet.get_by_id(data.get('multisig_id'))
        self.exported = data.get('exported', False)
        self.next_addr = data.get('next_addr', 0)
        self.addr_type = data.get('addr_type', None)

    async def choose_sw_wallet(self):
        result = await SWWalletChooserPage(initial_value=self.sw_wallet).show()
        if result is None:
            self.set_result(False)
            return

        self.sw_wallet = result

        # print('self.sw_wallet={}'.format(self.sw_wallet))
        self.goto(self.choose_sig_type)

    async def choose_sig_type(self):
        save_curr = True
        if len(self.sw_wallet['sig_types']) == 1:
            # print('Only 1 sig type...skipping')
            self.sig_type = self.sw_wallet['sig_types'][0]
            save_curr = False
        else:
            result = await SigTypeChooserPage(self.sw_wallet, initial_value=self.sig_type).show()
            if result is None:
                if not self.back():
                    self.set_result(False)
                return

            self.sig_type = result
            # print('sig_type={}'.format(self.sig_type))

        self.infer_wallet_info()

        # NOTE: Nothing uses this option at the moment, but leaving it here in case we need it for a
        #       new wallet later.
        if self.sw_wallet.get('select_addr_type', False):
            self.goto(self.choose_addr_type, save_curr=save_curr)
        else:
            self.goto(self.choose_export_mode, save_curr=save_curr)

    async def choose_addr_type(self):
        result = await AddressTypeChooserPage(initial_value=self.addr_type,
                                              options=self.sw_wallet.get('addr_options', None)).show()
        if result is None:
            if not self.back():
                self.set_result(False)
            return

        self.infer_wallet_info()

        self.addr_type = result
        # print('addr_type={}'.format(self.addr_type))
        self.goto(self.choose_export_mode)

    async def choose_export_mode(self):
        save_curr = True
        # We can skip this step if there is only a single export mode
        if len(self.sw_wallet['export_modes']) == 1:
            # print('Only 1 export mode...skipping')
            self.export_mode = self.sw_wallet['export_modes'][0]
            # print('self.export_mode[\'id\']={}, self.export_mode={}'.format(self.export_mode['id'], self.export_mode))
            save_curr = False
        else:
            result = await ExportModeChooserPage(self.sw_wallet, initial_value=self.export_mode).show()
            if result is None:
                if not self.back():
                    self.set_result(False)
                return
            self.export_mode = result

        # print('export_mode={}'.format(self.export_mode))
        self.goto(self.show_connect_message, save_curr=save_curr)

    async def show_connect_message(self):
        if self.export_mode['id'] == EXPORT_MODE_QR:
            msg = self.get_custom_text(
                'pairing_qr', 'Next, scan the QR code on the following screen into {}.'.format(self.sw_wallet['label']))
        elif self.export_mode['id'] == EXPORT_MODE_MICROSD:
            ext = self.export_mode.get('ext_multisig', '.json') if self.is_multisig(
            ) else self.export_mode.get('ext', '.json')
            msg = self.get_custom_text(
                'pairing_microsd', 'Next, Passport will save a {} file to your microSD card to use with {}.'.format(
                    ext, self.sw_wallet['label']))

        result = await InfoPage(
            icon=lv.LARGE_ICON_CONNECT,
            text=msg,
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        # Next state
        if self.export_mode['id'] == EXPORT_MODE_QR:
            self.goto(self.export_by_qr)
        elif self.export_mode['id'] == EXPORT_MODE_MICROSD:
            self.goto(self.export_by_microsd)

    async def export_by_qr(self):
        # Run the software wallet's associated export function to get the data
        (data, self.acct_info, _error) = await spinner_task(
            'Preparing Data',
            create_wallet_export_task,
            args=[self.sig_type['create_wallet'],
                  self.sw_wallet,
                  self.addr_type,
                  self.acct_num,
                  self.is_multisig(),
                  self.sig_type.get('legacy', False),
                  # Export mode
                  'qr',
                  self.export_mode['qr_type']])

        qr_type = self.export_mode['qr_type']

        # Show the QR code
        result = await ShowQRPage(
            statusbar={'title': 'CONNECT', 'icon': 'ICON_CONNECT'},
            qr_type=qr_type,
            qr_data=data).show()
        if result is False:
            if not self.back():
                self.set_result(False)
            return

        self.exported = True

        # If multisig, we need to import the quorum/config info first, else go right to validating the first
        # receive address from the wallet.
        if self.is_multisig():
            # Only perform multisig import if wallet does not prevent it
            if not self.is_skip_multisig_import_enabled():
                self.goto_multisig_import_mode()

            # Only perform address validation if wallet does not prevent it
            if self.is_skip_address_verification_enabled():
                if self.is_force_multisig_policy_enabled():
                    info_text = "For compatibility with {}, Passport will set your " \
                                "Multisig Policy to Skip Verification.".format(self.sw_wallet['label'])
                    result = await InfoPage(text=info_text).show()
                    if not result:
                        if not self.back():
                            self.set_result(False)
                            return
                    else:
                        common.settings.set('multisig_policy', TRUST_PSBT)
                        self.goto(self.complete)
                else:
                    self.goto(self.complete)
        else:
            self.goto_address_verification_method(save_curr=False)

    async def export_by_microsd(self):
        from utils import xfp2str, get_folder_path
        from flows import SaveToMicroSDFlow
        from public_constants import DIR_WALLET_CONFIGS

        # Run the software wallet's associated export function to get the data
        (data, self.acct_info, _error) = await spinner_task(
            'Preparing Data',
            create_wallet_export_task,
            args=[self.sig_type['create_wallet'],
                  self.sw_wallet,
                  self.addr_type,
                  self.acct_num,
                  self.is_multisig(),
                  self.sig_type.get('legacy', False),
                  # Export mode
                  'microsd',
                  None])

        data_hash = bytearray(32)
        foundation.sha256(data, data_hash)

        # Write the data to SD with the filename the wallet prefers
        if self.is_multisig():
            filename_pattern = self.export_mode['filename_pattern_multisig']
        else:
            filename_pattern = self.export_mode['filename_pattern']

        filename = filename_pattern.format(hash=data_hash,
                                           acct=self.acct_num,
                                           xfp=xfp2str(common.settings.get('xfp')).lower())

        save_result = await SaveToMicroSDFlow(filename=filename,
                                              path=get_folder_path(DIR_WALLET_CONFIGS),
                                              data=data).run()

        if not save_result:
            self.set_result(False)
            return

        # Save the progress so that we can resume later
        self.exported = True

        # If multisig, we need to import the quorum/config info first, else go right to validating the first
        # receive address from the wallet.
        if self.is_multisig():
            # Only perform multisig import if wallet does not prevent it
            if not self.is_skip_multisig_import_enabled():
                self.goto_multisig_import_mode()
                return

            # Only perform address validation if wallet does not prevent it
            if self.is_skip_address_verification_enabled():
                if self.is_force_multisig_policy_enabled():
                    info_text = "For compatibility with {}, Passport will set your " \
                                "Multisig Policy to Skip Verification.".format(self.sw_wallet['label'])
                    result = await InfoPage(text=info_text).show()
                    if not result:
                        if not self.back():
                            self.set_result(False)
                            return
                    else:
                        common.settings.set('multisig_policy', TRUST_PSBT)
                        self.goto(self.complete)
                else:
                    self.goto(self.complete)
        else:
            self.goto_address_verification_method(save_curr=False)

    async def import_multisig_config_from_qr(self):
        msg = self.get_custom_text(
            'multisig_import_qr', 'Next, import the multisig configuration from {} via QR code.'.format(
                self.sw_wallet['label']))
        result = await InfoPage(card_header={'title': 'Import Multisig'},
                                text=msg,
                                left_micron=microns.Back).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        scan_result = await self.sig_type['import_qr']()
        if scan_result is None:
            # Retry
            return

        if scan_result.error is not None:
            # Show error
            self.set_result(False)
            return

        try:
            # Mulitsig config should be a bytes-like object that we decode to a string
            if isinstance(scan_result.data, ur.Value):
                self.multisig_import_data = scan_result.data.unwrap_bytes().decode('utf-8')
            elif isinstance(scan_result.data, str):
                self.multisig_import_data = scan_result.data

            # from utils import to_str
            # print('MS Data: {}'.format(to_str(self.multisig_import_data)))
        except BaseException as e:
            await ErrorPage(text='Unexpected data format: {}'.format(e)).show()
            return

        self.goto(self.do_multisig_config_import)

    async def import_multisig_config_from_microsd(self):
        msg = self.get_custom_text('multisig_import_microsd',
                                   'Next, import the multisig configuration from {} via microSD card.'.format(
                                       self.sw_wallet['label']))

        result = await InfoPage(card_header={'title': 'Import Multisig'},
                                text=msg,
                                left_micron=microns.Back).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        self.multisig_import_data = await self.sig_type['import_microsd']()
        if self.multisig_import_data is None:
            # Retry
            return

        self.goto(self.do_multisig_config_import)

    async def do_multisig_config_import(self):
        from multisig_wallet import MultisigWallet

        try:
            ms = await MultisigWallet.from_file(self.multisig_import_data)
        except BaseException as e:
            if e.args is None or len(e.args) == 0:
                self.error = "Multisig Import Error"
            else:
                self.error = e.args[0]
            self.goto(self.show_error)
            return
        # if ms is not None:
        #     print('New MS: {}'.format(ms.serialize()))

        # Show the wallet to the user
        result = await ImportMultisigWalletFlow(ms).run()
        if not result:
            # The wallet was probably a duplicate or some other error occured
            self.set_result(False)
            return

        # Remember it for the latter states after this
        self.multisig_wallet = ms

        # Only perform address validation if wallet does not prevent it
        if self.is_skip_address_verification_enabled():
            if self.is_force_multisig_policy_enabled():
                info_text = "For compatibility with {}, Passport will set your " \
                            "Multisig Policy to Skip Verification.".format(self.sw_wallet['label'])
                result = await InfoPage(text=info_text).show()
                if not result:
                    if not self.back():
                        self.set_result(False)
                        return
                else:
                    common.settings.set('multisig_policy', TRUST_PSBT)
                    self.goto(self.complete)
            else:
                self.goto(self.complete)
        else:
            self.goto_address_verification_method()

    async def scan_rx_address_intro(self):
        msgs = ['Next, let\'s check that the wallet connected correctly.',
                'On the next page, scan a receive address from {}.'.format(self.sw_wallet['label'])
                ]

        result = await InfoPage(
            icon=lv.LARGE_ICON_CONNECT,
            text=msgs,
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        self.goto(self.scan_rx_address)

    async def scan_rx_address(self):
        from flows import VerifyAddressFlow

        result = await VerifyAddressFlow(sig_type=self.sig_type, multisig_wallet=self.multisig_wallet).run()
        if result:
            self.goto(self.complete)
        else:
            result = await QuestionPage(
                text='Unable to verify receive address. Retry?',
                right_micron=microns.Retry).show()
            if result:
                return
            else:
                await InfoPage(text='Skipping address verification.').show()
                self.set_result(False)

    async def show_rx_address_intro(self):
        from pages import InfoPage
        import microns

        msgs = ['Next, let\'s check that the wallet connected correctly.',
                '{name} should display a list of addresses which belong to this Passport.'.format(
                    name=self.sw_wallet['label']),
                'Ensure the first address matches the one shown on the next screen.'
                ]

        result = await InfoPage(
            text=msgs,
            card_header={'title': 'Verify Addresses'},
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        self.goto(self.show_rx_address)

    async def show_rx_address(self):
        from utils import split_to_lines
        from pages import LongTextPage
        from math import ceil
        NUM_ADDRESSES = 1

        (addresses, error) = await spinner_task(
            'Generating Address',
            generate_addresses_task,
            args=[0, NUM_ADDRESSES, self.addr_type, self.acct_num, self.multisig_wallet])

        if error is not None:
            await ErrorPage(text='Unable to generate address for verification').show()
            self.set_result(False)
            return

        # Show the first address to the user
        msg = '\nFirst Address\n\n'

        for entry in addresses:
            _, address = entry
            # Split to three lines for readability (addresses are 27-34 characters)
            max_line_len = ceil(len(address) / 3)
            msg += split_to_lines(address, max_line_len)

        result = await LongTextPage(text=msg, card_header={'title': 'Verify Address'}, centered=True).show()
        if not result:
            if not self.back():
                self.set_result(False)
            return

        self.goto(self.complete)

    async def complete(self):
        await SuccessPage(text='Connection Complete').show()
        self.set_result(True)

    async def show_error(self):
        await ErrorPage(text=self.error).show()
        self.error = None
        self.reset(self.choose_sig_type)

    # ===========================================================================================
    # Helper functions
    # ===========================================================================================

    def is_multisig(self):
        return self.sig_type['id'] == 'multisig'

    def is_skip_address_verification_enabled(self):
        if 'skip_address_validation' in self.sw_wallet:
            return self.sw_wallet['skip_address_validation']
        else:
            return False

    def is_skip_multisig_import_enabled(self):
        if 'skip_multisig_import' in self.sw_wallet:
            return self.sw_wallet['skip_multisig_import']
        else:
            return False

    def is_force_multisig_policy_enabled(self):
        if 'force_multisig_policy' in self.sw_wallet:
            return self.sw_wallet['force_multisig_policy']
        else:
            return False

    def goto_address_verification_method(self, save_curr=True):
        method = self.sw_wallet.get('address_validation_method', 'scan_rx_address')
        if method == 'scan_rx_address':
            self.goto(self.scan_rx_address_intro, save_curr=save_curr)
        elif method == 'show_address':
            self.goto(self.show_rx_address_intro, save_curr=save_curr)

    def goto_multisig_import_mode(self):
        if 'multisig_import_mode' in self.export_mode:
            if self.export_mode['multisig_import_mode'] == EXPORT_MODE_QR:
                self.goto(self.import_multisig_config_from_qr, save_curr=False)
            else:
                self.goto(self.import_multisig_config_from_microsd, save_curr=False)
        elif self.export_mode['id'] == EXPORT_MODE_QR:
            self.goto(self.import_multisig_config_from_qr, save_curr=False)
        else:
            self.goto(self.import_multisig_config_from_microsd, save_curr=False)

    def get_custom_text(self, field, default_text):
        if self.sw_wallet:
            ct = self.sw_wallet.get('custom_text')
            if ct:
                return ct.get(field, default_text)

        return default_text

    def infer_wallet_info(self, address=None, ms_wallet=None):
        # Ensure we have an addr_type, if possible yet
        if not self.addr_type:
            if self.sig_type['addr_type']:
                self.addr_type = self.sig_type['addr_type']
            elif self.acct_info and len(self.acct_info) == 1:
                self.addr_type = self.acct_info[0]['fmt']

        # If we now have the necessary parts, build the deriv_path
        if self.addr_type is not None:
            self.deriv_path = get_deriv_path_from_addr_type_and_acct(self.addr_type, self.acct_num, self.is_multisig())

        # If we didn't figure out the deriv_path yet, try to do it now
        if not self.deriv_path:
            if self.acct_info and len(self.acct_info) == 1:
                self.deriv_path = self.acct_info[0]['deriv']

            elif address:
                # We can derive it from the address now
                if not self.addr_type:  # Should be a redundant condition
                    self.addr_type = get_addr_type_from_address(address, self.is_multisig())

                self.deriv_path = get_deriv_path_from_address_and_acct(address, self.acct_num, self.is_multisig())

                if ms_wallet is not None:
                    assert self.deriv_path == ms_wallet.my_deriv

            elif ms_wallet:
                # If the address was skipped, but we have the multisig wallet, get the derivation from it directly
                self.deriv_path = ms_wallet.my_deriv

                # If we still don't have the addr_type, we should be able to infer it from the deriv_path
                if not self.addr_type:
                    self.addr_type = get_addr_type_from_deriv(self.deriv_path)
