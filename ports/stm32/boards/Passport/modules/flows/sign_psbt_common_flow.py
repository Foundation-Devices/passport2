# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# sign_psbt_common_flow.py - Sign a PSBT from a microSD card

import lvgl as lv
from flows import Flow
import microns
from pages.chooser_page import ChooserPage
from styles.colors import HIGHLIGHT_TEXT_HEX, BLACK_HEX
from tasks import sign_psbt_task, validate_psbt_task
import gc
from utils import spinner_task, recolor, stylize_address, start_task


class SignPsbtCommonFlow(Flow):
    def __init__(self, psbt_len):
        import chains
        super().__init__(initial_state=self.validate_psbt, name='SignPsbtCommonFlow')
        self.progress_page = None
        self.details = None
        self.psbt_len = psbt_len
        self.chain = chains.current_chain()
        self.header = 'Transaction Info'
        self.first_output = True
        self.first_change = True
        self.output_addresses = None
        self.change_addresses = None

    async def validation_on_done(self, details, message=None, error=None):
        self.details = details
        self.error = error
        self.error_message = message
        self.progress_page.set_result(error is None)

    def on_event(self, event_type, data):
        if event_type == 'progress':
            self.progress_page.set_progress(data)
        elif event_type == 'output_address':
            if self.first_output:
                self.first_output = False
            else:
                self.output_addresses.write('\n')
            address, amount = data
            amount = ' '.join(self.chain.render_value(amount))
            address = stylize_address(address)

            self.output_addresses.write('\n{}\n{}\n\n{}\n{}'.format(
                recolor(HIGHLIGHT_TEXT_HEX, 'Amount'),
                amount,
                recolor(HIGHLIGHT_TEXT_HEX, 'Destination'),
                address))
        elif event_type == 'change_address':
            if self.first_change:
                self.first_change = False
            else:
                self.change_addresses.write('\n')
            address, _ = data
            self.change_addresses.write(stylize_address(address))

    async def validate_psbt(self):
        import uio
        from pages import ErrorPage, ProgressPage

        self.first_output = True
        self.first_change = True
        self.output_addresses = uio.StringIO()
        self.change_addresses = uio.StringIO()

        self.progress_page = ProgressPage(text='Validating transaction', left_micron=None, right_micron=None)
        self.validate_task = start_task(validate_psbt_task(self.validation_on_done, self.on_event, self.psbt_len))

        result = await self.progress_page.show()
        if result:
            self.goto(self.check_multisig_import)
        else:
            await ErrorPage(self.error_message).show()
            self.set_result(None)

    async def check_multisig_import(self):
        from flows import ImportMultisigWalletFlow
        from pages import ErrorPage

        # Based on the import mode and whether this already exists, the validation step
        # will have set this flag.
        # if self.details.multisig_import_needs_approval:
        #     result = await ImportMultisigWalletFlow(self.details.active_multisig).run()
        #     if not result:
        #         text = 'The transaction can still be signed, but this multisig config will not be saved.'
        #         result2 = await ErrorPage(text=text, left_micron=microns.Back).show()
        #         if not result2:
        #             return

        self.goto(self.show_transaction_details)

    async def show_transaction_details(self):
        import uio
        from pages import LongTextPage, ErrorPage
        from public_constants import MARGIN_FOR_ADDRESSES

        try:
            rendered_details = uio.StringIO()
            if self.details.is_self_send():
                rendered_details.write("\n{}\n".format(recolor(HIGHLIGHT_TEXT_HEX, 'Self-Send')))
            rendered_details.write(self.output_addresses.getvalue())

            gc.collect()

            result = await LongTextPage(
                text=rendered_details.getvalue(),
                centered=True,
                card_header={'title': self.header},
                margins=MARGIN_FOR_ADDRESSES,
            ).show()
            if result:
                if self.details.is_self_send():
                    self.goto(self.show_warnings)
                else:
                    self.goto(self.show_change)
            else:
                self.set_result(None)

        except MemoryError:
            await ErrorPage(text='Transaction is too complex.').show()
            self.set_result(None)

        except BaseException as e:
            await ErrorPage(text='Invalid PSBT: {}'.format(e)).show()
            self.set_result(None)

    async def show_change(self):
        from pages import LongTextPage, ErrorPage
        from public_constants import MARGIN_FOR_ADDRESSES

        try:
            msg = self.render_change_text()
            result = await LongTextPage(
                text=msg,
                centered=True,
                card_header={'title': self.header},
                margins=MARGIN_FOR_ADDRESSES
            ).show()
            gc.collect()
            if not result:
                self.back()
            else:
                self.goto(self.show_warnings)
        except Exception as e:
            await ErrorPage(text='Invalid PSBT: {}'.format(e)).show()
            self.set_result(False)

    async def show_warnings(self):
        from pages import LongTextPage

        warnings = self.render_warnings()
        gc.collect()
        # print('warnings = "{}"'.format(warnings))

        if warnings is not None:
            result = await LongTextPage(
                text=warnings,
                centered=True,
                card_header={'title': self.header}
            ).show()
            if not result:
                self.back()
            else:
                self.set_result(None)
                # self.goto(self.sign_transaction) TODO
        else:
            self.set_result(None)
            # self.goto(self.sign_transaction) TODO

    async def sign_transaction(self):
        from tasks import double_check_psbt_change_task
        from utils import spinner_task
        from pages import ErrorPage, QuestionPage

        gc.collect()

        result = await QuestionPage(text='Sign transaction?', right_micron=microns.Sign).show()  # Change to Sign icon
        if not result:
            options = [{'label': 'Cancel', 'value': True},
                       {'label': 'Review Details', 'value': False}]

            should_cancel = await QuestionPage(text='Cancel this transaction?').show()
            if should_cancel:
                self.set_result(None)
            else:
                self.back()
        else:
            # TODO: Why do this here instead of in validate?
            (error_msg, error) = await spinner_task('Signing Transaction',
                                                    double_check_psbt_change_task, args=[self.details])

            gc.collect()
            if error is not None:
                await ErrorPage(error_msg).show()
                self.set_result(None)
                return

            (error_msg, error) = await spinner_task('Signing Transaction',
                                                    sign_psbt_task, args=[self.details])
            gc.collect()
            if error is not None:
                await ErrorPage(error_msg).show()
                self.set_result(None)
                return

            # print('>>>>>>>>> SIGNED!!!!!')
            self.set_result(self.details)
            # or in error self.set_result(None)

    def render_change_text(self):
        import uio

        # Produce text report of what the "change" outputs are (based on our opinion).
        # - we don't really expect all users to verify these outputs, but just in case.
        # - show the total amount, and list addresses
        with uio.StringIO() as msg:
            msg.write('\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Amount')))

            total = self.details.total_change()
            if total == 0:
                msg.write('\nNo change')
                return msg.getvalue()

            total_val = ' '.join(self.chain.render_value(total))
            msg.write('\n%s\n' % total_val)

            multiple_addresses = not self.first_change
            if multiple_addresses:
                msg.write('\n{}\n{}\n'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Address'),
                                              self.change_addresses.getvalue()))
            else:
                msg.write('\n{}\n{}\n'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Address'),
                                              self.change_addresses.getvalue()))

            return msg.getvalue()

    def render_warnings(self):
        import uio

        with uio.StringIO() as msg:
            # gc.collect()

            fee = self.details.fee()
            amount, units = self.chain.render_value(fee)
            msg.write('\n{}\n{} {} '.format(recolor(HIGHLIGHT_TEXT_HEX, 'Network Fee'), amount, units))

            warnings = []

            if self.details.is_self_send():
                fee_percentage = (fee / (fee + self.details.total_with_change())) * 100
                if fee_percentage >= 5:
                    warnings.append(('Big Fee', 'Network fee is %.1f%% of total amount' % fee_percentage))
            else:
                total_non_change = self.details.total_with_change() - self.details.total_change()
                if fee > total_non_change:
                    warnings.append(('Huge Fee', 'Network fee is larger than the amount you are sending.'))
                else:
                    fee_percentage = (fee / (fee + total_non_change)) * 100
                    if fee_percentage >= 5:
                        warnings.append(('Big Fee', 'Network fee is %.1f%% of total amount' % fee_percentage))

            if len(warnings) > 0:
                msg.write('\n\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Warnings')))
                for label, m in warnings:
                    msg.write('\n{}\n{}\n'.format(recolor(BLACK_HEX, label), m))
                    gc.collect()

            return msg.getvalue()
