# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from flows import Flow, SaveToMicroSDFlow


def _decode_policy(data):
    import chains
    import stash
    from policy_transport import decode_policy_transport

    chain = chains.current_chain()
    with stash.SensitiveValues() as sv:
        def derive_node(path):
            node = sv.node.clone()
            for element in path:
                node.derive(element)
            return node

        return decode_policy_transport(data, chain, sv.get_xfp(), derive_node)


class ImportWalletPolicyFlow(Flow):
    def __init__(self, policy):
        self.policy = policy
        self.error = None
        self.key_names = list(policy.key_names)
        self.external_key_indexes = tuple(
            index for index in range(len(policy.keys))
            if index not in policy.owned_key_indexes)
        self.key_name_position = 0
        super().__init__(initial_state=self.choose_name, name='ImportWalletPolicyFlow')

    async def choose_name(self):
        import microns
        from pages import TextInputPage
        from wallet_policy import MAX_POLICY_NAME_LENGTH

        result = await TextInputPage(
            title='Wallet Policy Name', initial_text=self.policy.name,
            max_length=MAX_POLICY_NAME_LENGTH, left_micron=microns.Cancel,
            right_micron=microns.Checkmark).show()
        if result is None:
            self.set_result(False)
            return
        try:
            self.policy = self.policy.rename(result)
        except BaseException as exc:
            self.error = str(exc)
            self.goto(self.show_error)
            return
        self.key_name_position = 0
        self.goto(self.choose_key_name)

    async def choose_key_name(self):
        import microns
        from pages import ErrorPage, TextInputPage
        from policy_display import format_fingerprint, suggested_key_name
        from wallet_policy import MAX_KEY_NAME_LENGTH

        if self.key_name_position >= len(self.external_key_indexes):
            try:
                self.policy = self.policy.name_keys(self.key_names)
            except BaseException as exc:
                self.error = str(exc)
                self.goto(self.show_error)
                return
            self.goto(self.show_overview)
            return

        key_index = self.external_key_indexes[self.key_name_position]
        key = self.policy.keys[key_index]
        initial = self.key_names[key_index] or suggested_key_name(self.policy, key_index)
        result = await TextInputPage(
            card_header={'title': 'Name Signer'},
            title='Fingerprint\n{}'.format(format_fingerprint(key.fingerprint)),
            initial_text=initial, max_length=MAX_KEY_NAME_LENGTH,
            left_micron=microns.Back, right_micron=microns.Checkmark).show()
        if result is None:
            if self.key_name_position:
                self.key_name_position -= 1
            else:
                self.back()
            return
        if not result:
            await ErrorPage('Enter a name for this signer.').show()
            return
        self.key_names[key_index] = result
        self.key_name_position += 1

    async def show_overview(self):
        from flows import SeriesOfPagesFlow
        from pages import LongTextPage
        page_args = [{
            'card_header': {'title': 'Wallet policy'},
            'text': text,
            'centered': not text.startswith('Path '),
        } for text in self.policy.format_review_pages()]
        result = await SeriesOfPagesFlow(LongTextPage, page_args).run()
        if result:
            self.goto(self.choose_technical_details)
        else:
            if self.external_key_indexes:
                self.key_name_position = len(self.external_key_indexes) - 1
            self.back()

    async def choose_technical_details(self):
        import microns
        from pages import YesNoChooserPage
        result = await YesNoChooserPage(
            text='Review the raw descriptor and extended public keys?',
            yes_text='Technical details', no_text='Continue',
            initial_value=False, left_micron=microns.Back).show()
        if result is None:
            self.back()
        elif result:
            self.goto(self.show_details)
        else:
            self.goto(self.confirm_import)

    async def show_details(self):
        from pages import LongTextPage
        result = await LongTextPage(
            card_header={'title': 'Technical details'},
            text=self.policy.format_details(), centered=False).show()
        if result:
            self.goto(self.confirm_import)
        else:
            self.back()

    async def confirm_import(self):
        from pages import LongQuestionPage
        from utils import escape_text
        text = 'Register {}?\n\n{}\n\nPolicy checksum\n{}'.format(
            escape_text(self.policy.name), self.policy.format_confirmation(),
            self.policy.descriptor_check())
        result = await LongQuestionPage(text=text).show()
        if result:
            self.goto(self.save_policy)
        else:
            self.set_result(False)

    async def save_policy(self):
        from common import settings
        from errors import Error
        from pages import ErrorPage, SuccessPage
        from tasks.wallet_policy_task import save_wallet_policy_task
        from utils import spinner_task
        from wallet_policy import WalletPolicyRegistry

        if WalletPolicyRegistry(settings).get(self.policy.policy_id):
            await ErrorPage('This wallet policy is already registered.').show()
            self.set_result(False)
            return
        error, = await spinner_task(
            'Saving wallet policy', save_wallet_policy_task, args=[self.policy])
        if error is Error.USER_SETTINGS_FULL:
            await ErrorPage('Not enough settings space to save this wallet policy.').show()
            self.set_result(False)
            return
        if error is not None:
            await ErrorPage('Unable to save wallet policy.').show()
            self.set_result(False)
            return
        from flows import AutoBackupFlow
        await AutoBackupFlow().run()
        await SuccessPage(
            'Wallet policy registered\n\nChoose what you would like to do next.').show()
        self.goto(self.choose_next_action)

    async def choose_next_action(self):
        import microns
        from pages import ChooserPage
        options = [
            {'label': 'Verify an address', 'value': 'verify'},
            {'label': 'Back up wallet policy', 'value': 'backup'},
        ]
        if self.external_key_indexes:
            options.append({'label': 'Label signer keys', 'value': 'name_keys'})
        options.extend([
            {'label': 'View technical details', 'value': 'details'},
            {'label': 'Finish', 'value': 'finish'},
        ])
        result = await ChooserPage(
            card_header={'title': 'Wallet registered'},
            text='Recommended next steps', options=options,
            initial_value='verify', scroll_fix=True,
            left_micron=microns.Back).show()
        if result is None or result == 'finish':
            self.set_result(True)
        elif result == 'verify':
            self.goto(self.verify_first_address)
        elif result == 'backup':
            self.goto(self.choose_backup_method)
        elif result == 'name_keys':
            self.goto(self.label_signer_keys)
        else:
            self.goto(self.view_registered_details)

    async def verify_first_address(self):
        from flows import VerifyAddressFlow
        result = await VerifyAddressFlow(
            sig_type='policy', wallet_policy=self.policy).run()
        if result:
            # Registration is complete and the receive address is verified.
            # Exit the import flow so the parent Wallet Policies menu refreshes.
            self.set_result(True)
        else:
            self.goto(self.choose_next_action, save_curr=False)

    async def choose_backup_method(self):
        import microns
        from pages import YesNoChooserPage
        result = await YesNoChooserPage(
            text='How would you like to back up this wallet policy?',
            yes_text='QR code', no_text='microSD',
            initial_value=True, left_micron=microns.Back).show()
        if result is None:
            self.goto(self.choose_next_action, save_curr=False)
        elif result:
            self.goto(self.backup_via_qr)
        else:
            self.goto(self.backup_via_microsd)

    async def backup_via_qr(self):
        await ExportWalletPolicyQRFlow(context=self.policy.policy_id).run()
        self.goto(self.choose_next_action, save_curr=False)

    async def backup_via_microsd(self):
        await ExportWalletPolicyMicroSDFlow(context=self.policy.policy_id).run()
        self.goto(self.choose_next_action, save_curr=False)

    async def label_signer_keys(self):
        result = await NameWalletPolicyKeysFlow(context=self.policy.policy_id).run()
        if result:
            from common import settings
            from wallet_policy import WalletPolicyRegistry
            self.policy = WalletPolicyRegistry(settings).get(self.policy.policy_id)
        self.goto(self.choose_next_action, save_curr=False)

    async def view_registered_details(self):
        import microns
        from pages import LongTextPage
        await LongTextPage(
            card_header={'title': 'Technical details'},
            text=self.policy.format_details(), centered=False,
            right_micron=microns.Checkmark).show()
        self.goto(self.choose_next_action, save_curr=False)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)


class ImportWalletPolicyFromQRFlow(Flow):
    def __init__(self):
        self.error = None
        super().__init__(initial_state=self.scan, name='ImportWalletPolicyFromQRFlow')

    async def scan(self):
        from data_codecs.qr_type import QRType
        from flows import ScanQRFlow
        from foundation import ur

        result = await ScanQRFlow(
            qr_types=[QRType.QR, QRType.UR2], ur_types=[ur.Value.BYTES],
            data_description='a wallet policy').run()
        if result is None:
            self.set_result(False)
            return
        try:
            data = result.unwrap_bytes() if hasattr(result, 'unwrap_bytes') else result
            policy = _decode_policy(data)
        except BaseException as exc:
            self.error = str(exc) or 'Wallet Policy Import Error'
            self.goto(self.show_error)
            return
        result = await ImportWalletPolicyFlow(policy).run()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.error = None
        self.reset(self.scan)


class ImportWalletPolicyFromMicroSDFlow(Flow):
    def __init__(self):
        self.error = None
        super().__init__(initial_state=self.choose_file,
                         name='ImportWalletPolicyFromMicroSDFlow')

    async def choose_file(self):
        from flows import FilePickerFlow
        from tasks import read_file_task
        from utils import spinner_task

        result = await FilePickerFlow(show_folders=True).run()
        if result is None:
            self.set_result(False)
            return
        _, full_path, is_folder = result
        if is_folder:
            return
        data, error = await spinner_task('Reading policy', read_file_task, args=[full_path])
        if error is not None:
            self.error = 'Unable to read wallet policy file.'
            self.goto(self.show_error)
            return
        try:
            policy = _decode_policy(data)
        except BaseException as exc:
            self.error = str(exc) or 'Wallet Policy Import Error'
            self.goto(self.show_error)
            return
        result = await ImportWalletPolicyFlow(policy).run()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.error = None
        self.reset(self.choose_file)


class ViewWalletPolicyFlow(Flow):
    def __init__(self, context=None):
        from common import settings
        from wallet_policy import WalletPolicyRegistry
        self.policy = WalletPolicyRegistry(settings).get(context)
        super().__init__(initial_state=self.show_overview, name='ViewWalletPolicyFlow')

    async def show_overview(self):
        from flows import SeriesOfPagesFlow
        from pages import ErrorPage, LongTextPage
        if self.policy is None:
            await ErrorPage('Wallet policy was not found.').show()
            self.set_result(False)
            return
        page_args = [{
            'card_header': {'title': 'Wallet policy'},
            'text': text,
            'centered': not text.startswith('Path '),
        } for text in self.policy.format_review_pages()]
        result = await SeriesOfPagesFlow(LongTextPage, page_args).run()
        if result:
            self.goto(self.choose_technical_details)
        else:
            self.set_result(False)

    async def choose_technical_details(self):
        import microns
        from pages import YesNoChooserPage
        result = await YesNoChooserPage(
            text='Review the raw descriptor and extended public keys?',
            yes_text='Technical details', no_text='Done',
            initial_value=False, left_micron=microns.Back).show()
        if result is None:
            self.back()
        elif result:
            self.goto(self.show_details)
        else:
            self.set_result(True)

    async def show_details(self):
        import microns
        from pages import LongTextPage
        result = await LongTextPage(
            card_header={'title': 'Technical details'},
            text=self.policy.format_details(), centered=False,
            right_micron=microns.Checkmark).show()
        if result:
            self.set_result(True)
        else:
            self.back()


class RenameWalletPolicyFlow(Flow):
    def __init__(self, context=None):
        from common import settings
        from wallet_policy import WalletPolicyRegistry
        self.policy = WalletPolicyRegistry(settings).get(context)
        super().__init__(initial_state=self.choose_name, name='RenameWalletPolicyFlow')

    async def choose_name(self):
        import microns
        from pages import ErrorPage, TextInputPage
        from wallet_policy import MAX_POLICY_NAME_LENGTH
        if self.policy is None:
            await ErrorPage('Wallet policy was not found.').show()
            self.set_result(False)
            return
        result = await TextInputPage(
            title='Wallet Policy Name', initial_text=self.policy.name,
            max_length=MAX_POLICY_NAME_LENGTH, left_micron=microns.Cancel,
            right_micron=microns.Checkmark).show()
        if result is None:
            self.set_result(False)
            return
        from tasks.wallet_policy_task import rename_wallet_policy_task
        from utils import spinner_task
        error, = await spinner_task(
            'Renaming policy', rename_wallet_policy_task,
            args=[self.policy.policy_id, result])
        if error is not None:
            await ErrorPage('Unable to rename wallet policy.').show()
            self.set_result(False)
            return
        from flows import AutoBackupFlow
        from pages import SuccessPage
        await SuccessPage('Wallet policy renamed').show()
        await AutoBackupFlow().run()
        self.set_result(True)


class NameWalletPolicyKeysFlow(Flow):
    def __init__(self, context=None):
        from common import settings
        from wallet_policy import WalletPolicyRegistry
        self.policy = WalletPolicyRegistry(settings).get(context)
        self.key_names = list(self.policy.key_names) if self.policy else []
        self.external_key_indexes = tuple(
            index for index in range(len(self.policy.keys))
            if index not in self.policy.owned_key_indexes) if self.policy else ()
        self.key_name_position = 0
        super().__init__(initial_state=self.choose_key_name,
                         name='NameWalletPolicyKeysFlow')

    async def choose_key_name(self):
        import microns
        from pages import ErrorPage, TextInputPage
        from policy_display import format_fingerprint, suggested_key_name
        from wallet_policy import MAX_KEY_NAME_LENGTH

        if self.policy is None:
            await ErrorPage('Wallet policy was not found.').show()
            self.set_result(False)
            return
        if not self.external_key_indexes:
            await ErrorPage('This wallet policy has no external signers.').show()
            self.set_result(False)
            return
        if self.key_name_position >= len(self.external_key_indexes):
            self.goto(self.save_key_names)
            return

        key_index = self.external_key_indexes[self.key_name_position]
        key = self.policy.keys[key_index]
        initial = self.key_names[key_index] or suggested_key_name(self.policy, key_index)
        result = await TextInputPage(
            card_header={'title': 'Name Signer'},
            title='Fingerprint\n{}'.format(format_fingerprint(key.fingerprint)),
            initial_text=initial, max_length=MAX_KEY_NAME_LENGTH,
            left_micron=microns.Back, right_micron=microns.Checkmark).show()
        if result is None:
            if self.key_name_position:
                self.key_name_position -= 1
            else:
                self.set_result(False)
            return
        if not result:
            await ErrorPage('Enter a name for this signer.').show()
            return
        self.key_names[key_index] = result
        self.key_name_position += 1

    async def save_key_names(self):
        from flows import AutoBackupFlow
        from pages import ErrorPage, SuccessPage
        from tasks.wallet_policy_task import rename_wallet_policy_keys_task
        from utils import spinner_task

        error, = await spinner_task(
            'Saving signer names', rename_wallet_policy_keys_task,
            args=[self.policy.policy_id, self.key_names])
        if error is not None:
            await ErrorPage('Unable to save signer names.').show()
            self.set_result(False)
            return
        await SuccessPage('Signer names saved').show()
        await AutoBackupFlow().run()
        self.set_result(True)


class DeleteWalletPolicyFlow(Flow):
    def __init__(self, context=None):
        from common import settings
        from wallet_policy import WalletPolicyRegistry
        self.policy = WalletPolicyRegistry(settings).get(context)
        super().__init__(initial_state=self.confirm, name='DeleteWalletPolicyFlow')

    async def confirm(self):
        from pages import ErrorPage, QuestionPage
        if self.policy is None:
            await ErrorPage('Wallet policy was not found.').show()
            self.set_result(False)
            return
        result = await QuestionPage(
            'Delete wallet policy?\n\n{}\n\nPassport will not sign it until reimported.'.format(
                self.policy.name)).show()
        if not result:
            self.set_result(False)
            return
        from tasks.wallet_policy_task import delete_wallet_policy_task
        from utils import spinner_task
        error, = await spinner_task(
            'Deleting policy', delete_wallet_policy_task,
            args=[self.policy.policy_id])
        if error is not None:
            await ErrorPage('Unable to delete wallet policy.').show()
            self.set_result(False)
            return
        from flows import AutoBackupFlow
        from pages import SuccessPage
        await SuccessPage('Wallet policy deleted').show()
        await AutoBackupFlow().run()
        self.set_result(True)


class ExportWalletPolicyQRFlow(Flow):
    def __init__(self, context=None):
        from common import settings
        from wallet_policy import WalletPolicyRegistry
        self.policy = WalletPolicyRegistry(settings).get(context)
        super().__init__(initial_state=self.show_qr, name='ExportWalletPolicyQRFlow')

    async def show_qr(self):
        from data_codecs.qr_type import QRType
        from foundation import ur
        from pages import ErrorPage, ShowQRPage
        from policy_transport import encode_policy_transport
        if self.policy is None:
            await ErrorPage('Wallet policy was not found.').show()
            self.set_result(False)
            return
        data = encode_policy_transport(self.policy).encode('utf-8')
        await ShowQRPage(qr_type=QRType.UR2, qr_data=ur.new_bytes(data)).show()
        self.set_result(True)


class ExportWalletPolicyMicroSDFlow(SaveToMicroSDFlow):
    def __init__(self, context=None):
        from common import settings
        from policy_transport import encode_policy_transport
        from public_constants import DIR_WALLET_CONFIGS
        from utils import get_folder_path
        from wallet_policy import WalletPolicyRegistry
        policy = WalletPolicyRegistry(settings).get(context)
        if policy is None:
            raise ValueError('Wallet policy was not found')
        safe_name = ''.join(ch if ('0' <= ch <= '9' or 'a' <= ch <= 'z' or
                                   'A' <= ch <= 'Z' or ch in '-_') else '_'
                            for ch in policy.name)
        super().__init__(
            filename='{}-policy.json'.format(safe_name),
            path=get_folder_path(DIR_WALLET_CONFIGS),
            data=encode_policy_transport(policy), success_text='wallet policy')
