# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
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
from utils import spinner_task, recolor


class SignPsbtCommonFlow(Flow):
    def __init__(self, psbt_len):
        import chains
        super().__init__(initial_state=self.validate_psbt, name='SignPsbtCommonFlow')
        self.psbt = None
        self.psbt_len = psbt_len
        self.chain = chains.current_chain()

    async def validate_psbt(self):
        from pages import ErrorPage

        (self.psbt, error_msg, error) = await spinner_task('Validating transaction', validate_psbt_task,
                                                           args=[self.psbt_len])
        # print('psbt={} error_msg={} error={}'.format(self.psbt, error_msg, error))
        if error is not None:
            await ErrorPage(error_msg).show()
            self.set_result(None)
        else:
            self.goto(self.check_multisig_import)

    async def check_multisig_import(self):
        from flows import ImportMultisigWalletFlow
        from pages import ErrorPage

        # Based on the import mode and whether this already exists, the validation step
        # will have set this flag.
        if self.psbt.multisig_import_needs_approval:
            result = await ImportMultisigWalletFlow(self.psbt.active_multisig).run()
            if not result:
                await ErrorPage(
                    'The transaction can still be signed, but this multisig config will not be saved.').show()

        self.goto(self.show_transaction_details)

    async def show_transaction_details(self):
        import uio
        from pages import LongTextPage, ErrorPage

        try:
            outputs = uio.StringIO()

            first = True
            for idx, tx_out in self.psbt.output_iter():
                outp = self.psbt.outputs[idx]
                if outp.is_change:
                    continue

                if first:
                    first = False
                else:
                    outputs.write('\n')

                outputs.write(self.render_output(tx_out))

            if first:
                # All outputs are change, so no amount is being "sent" to another wallet
                outputs.write('\n{}\nNone'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Amount')))

            # print('total_out={} total_in={}
            # change={}'.format=(self.psbt.total_value_out, self.psbt.total_value_in,
            # self.psbt.total_value_in - self.psbt.total_value_out))

            result = await LongTextPage(
                text=outputs.getvalue(),
                centered=True,
                card_header={'title': 'Transaction Details'}
            ).show()
            if result:
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

        try:
            msg = self.render_change_text()
            result = await LongTextPage(
                text=msg,
                centered=True,
                card_header={'title': 'Transaction Details'}
            ).show()
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
        # print('warnings = "{}"'.format(warnings))

        if warnings is not None:
            result = await LongTextPage(
                text=warnings,
                centered=True,
                card_header={'title': 'Transaction Details'}
            ).show()
            if not result:
                self.back()
            else:
                self.goto(self.sign_transaction)
        else:
            self.goto(self.sign_transaction)

    async def sign_transaction(self):
        from tasks import double_check_psbt_change_task
        from utils import spinner_task
        from pages import ErrorPage, QuestionPage

        result = await QuestionPage(text='Sign transaction?', right_micron=microns.Sign).show()  # Change to Sign icon
        if not result:
            options = [{'label': 'Cancel', 'value': True},
                       {'label': 'Review Details', 'value': False}]

            should_cancel = await ChooserPage(
                text='Cancel this transaction?',
                options=options,
                icon=lv.LARGE_ICON_QUESTION,
                initial_value=options[0].get('value')).show()
            if should_cancel:
                self.set_result(None)
            else:
                self.back()
        else:
            # TODO: Why do this here instead of in validate?
            (error_msg, error) = await spinner_task('Signing Transaction',
                                                    double_check_psbt_change_task, args=[self.psbt])
            if error is not None:
                await ErrorPage(error_msg).show()
                self.set_result(None)
                return

            (error_msg, error) = await spinner_task('Signing Transaction',
                                                    sign_psbt_task, args=[self.psbt])
            if error is not None:
                await ErrorPage(error_msg).show()
                self.set_result(None)
                return

            # print('>>>>>>>>> SIGNED!!!!!')
            self.set_result(self.psbt)
            # or in error self.set_result(None)

    def render_output(self, o):
        # Pretty-print a transactions output.
        # - expects CTxOut object
        # - gives user-visible string
        #
        val = ''.join(self.chain.render_value(o.nValue))
        dest = self.chain.render_address(o.scriptPubKey)

        return '\n{}\n{}\n\n{}\n{}'.format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Amount'),
            val,
            recolor(HIGHLIGHT_TEXT_HEX, 'Destination'),
            dest)

    def render_change_text(self):
        import uio

        # Produce text report of what the "change" outputs are (based on our opinion).
        # - we don't really expect all users to verify these outputs, but just in case.
        # - show the total amount, and list addresses
        with uio.StringIO() as msg:
            msg.write('\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Amount')))
            total = 0
            addrs = []
            # print('len(outputs)={}'.format(len(self.psbt.outputs)))
            for idx, tx_out in self.psbt.output_iter():
                outp = self.psbt.outputs[idx]
                if not outp.is_change:
                    continue
                # print('idx: {} output:{}'.format(idx, self.chain.render_address(tx_out.scriptPubKey)))
                total += tx_out.nValue
                addrs.append(self.chain.render_address(tx_out.scriptPubKey))

            if len(addrs) == 0:
                msg.write('\nNo change')
                return msg.getvalue()

            total_val = ' '.join(self.chain.render_value(total))

            msg.write('\n%s\n' % total_val)

            if len(addrs) == 1:
                msg.write('\n{}\n{}\n'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Address'), addrs[0]))
            else:
                msg.write('\n{}\n'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Addresses')))
                for a in addrs:
                    msg.write('%s\n\n' % a)

            return msg.getvalue()

    def render_warnings(self):
        import uio

        with uio.StringIO() as msg:
            # # mention warning at top
            # wl = len(self.psbt.warnings)
            # if wl == 1:
            #     msg.write('(1 warning below)\n\n')
            # elif wl >= 2:
            #     msg.write('(%d warnings below)\n\n' % wl)

            # gc.collect()

            fee = self.psbt.calculate_fee()
            if fee is not None:
                amount, units = self.chain.render_value(fee)
                msg.write('\n{}\n{} {} '.format(recolor(HIGHLIGHT_TEXT_HEX, 'Network Fee'), amount, units))

            # # NEW: show where all the change outputs are going
            # self.render_change_text(msg)
            # gc.collect()

            if self.psbt.warnings and len(self.psbt.warnings) > 0:
                msg.write('\n\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Warnings')))
                for label, m in self.psbt.warnings:
                    msg.write('\n{}\n{}\n'.format(recolor(BLACK_HEX, label), m))

            return msg.getvalue()
