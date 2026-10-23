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

from flows import Flow
import microns
from styles.colors import HIGHLIGHT_TEXT_HEX, BLACK_HEX
from tasks import validate_psbt_task
import gc
from utils import b2a_hex, escape_text, spinner_task, recolor, stylize_address


def render_op_return_message(message):
    # The review fonts only carry printable ASCII, and anything else is drawn as
    # nothing at zero width. A message the user can't see must never look like no
    # message, so fall back to its bytes in hex.
    if not message:
        return '(empty)'
    if not any('!' <= char <= '~' for char in message):
        return b2a_hex(message.encode()).decode()
    return escape_text(message)


class SignPsbtCommonFlow(Flow):
    def __init__(self, psbt_len):
        import chains
        super().__init__(initial_state=self.validate_psbt, name='SignPsbtCommonFlow')
        self.psbt = None
        self.psbt_len = psbt_len
        self.chain = chains.current_chain()
        self.header = 'Transaction Info'
        self.review_page_index = 0

    async def validate_psbt(self):
        (self.psbt, error_msg, error) = await spinner_task('Validating transaction', validate_psbt_task,
                                                           args=[self.psbt_len])
        # print('psbt={} error_msg={} error={}'.format(self.psbt, error_msg, error))
        if error is not None:
            await self.show_psbt_error(error_msg)
            self.set_result(None)
        else:
            if self.psbt.active_policy:
                self.header = 'Policy transaction'
            self.goto(self.check_multisig_import)

    async def show_psbt_error(self, error_msg):
        from pages import ErrorPage
        from psbt_display import format_psbt_error
        friendly, technical = format_psbt_error(error_msg)
        text = friendly
        if technical:
            text = [friendly, 'Technical details\n\n{}'.format(technical)]
        await ErrorPage(text=text).show()

    async def check_multisig_import(self):
        from flows import ImportMultisigWalletFlow
        from pages import ErrorPage
        from tasks import double_check_psbt_change_task

        # Based on the import mode and whether this already exists, the validation step
        # will have set this flag.
        if self.psbt.multisig_import_needs_approval:
            result = await ImportMultisigWalletFlow(self.psbt.active_multisig).run()
            if not result:
                self.set_result(None)
                return

        # Prove ownership before presenting an output as change.
        if any(output.is_change for output in self.psbt.outputs):
            gc.collect()
            (error_msg, error) = await spinner_task('Verifying change',
                                                    double_check_psbt_change_task, args=[self.psbt])
            gc.collect()
            if error is not None:
                await ErrorPage(error_msg).show()
                self.set_result(None)
                return

        self.goto(self.show_transaction_details)

    async def show_transaction_details(self):
        import common
        from animations.constants import TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
        from pages import LongTextPage, ErrorPage
        from public_constants import MARGIN_FOR_ADDRESSES

        try:
            while True:
                for page_index, text in enumerate(self.review_pages()):
                    if page_index < self.review_page_index:
                        continue
                    gc.collect()
                    result = await LongTextPage(
                        text=text,
                        centered=True,
                        card_header={'title': self.header},
                        margins=MARGIN_FOR_ADDRESSES,
                        require_scroll_to_end=True,
                    ).show()
                    if result:
                        self.review_page_index += 1
                        common.page_transition_dir = TRANSITION_DIR_PUSH
                    elif result is False and self.review_page_index > 0:
                        self.review_page_index -= 1
                        common.page_transition_dir = TRANSITION_DIR_POP
                        break
                    else:
                        self.set_result(None)
                        return
                else:
                    self.review_page_index = page_index
                    self.goto(self.show_policy_authorization)
                    return

        except MemoryError:
            await ErrorPage(text='Transaction is too complex.').show()
            self.set_result(None)

        except Exception as error:
            await ErrorPage(text=self.invalid_psbt_text(error)).show()
            self.set_result(None)

    def review_pages(self):
        output_count = sum(not output.is_change or self.psbt.self_send for output in self.psbt.outputs)
        output_number = 0
        for index, output in self.psbt.output_iter():
            if self.psbt.outputs[index].is_change and not self.psbt.self_send:
                continue
            output_number += 1
            title = 'Self-Send' if self.psbt.self_send else 'Output'
            title = recolor(HIGHLIGHT_TEXT_HEX, '{} {}/{}'.format(title, output_number, output_count))
            yield '{}\n{}'.format(title, self.render_output(output))

        if not self.psbt.self_send:
            yield self.render_change_text()
            change_count = sum(1 for output in self.psbt.outputs if output.is_change)
            change_number = 0
            for index, output in self.psbt.output_iter():
                if not self.psbt.outputs[index].is_change:
                    continue
                change_number += 1
                title = recolor(HIGHLIGHT_TEXT_HEX, 'Change {}/{}'.format(change_number, change_count))
                yield '{}\n{}'.format(title, self.render_output(output))

        fee_labels = ('Big Fee', 'Huge Fee', 'Unverified Fee')
        fee_text = self.render_fee()
        fee_warnings = [warning for warning in self.psbt.warnings if warning[0] in fee_labels]
        if fee_warnings:
            for warning in fee_warnings:
                yield '{}\n\n{}'.format(fee_text, self.render_warning(warning))
        else:
            yield fee_text

        warnings = [warning for warning in self.psbt.warnings if warning[0] not in fee_labels]
        for index, warning in enumerate(warnings):
            title = recolor(HIGHLIGHT_TEXT_HEX, 'Warning {}/{}'.format(index + 1, len(warnings)))
            yield '{}\n\n{}'.format(title, self.render_warning(warning))

    async def show_policy_authorization(self):
        policy = self.psbt.active_policy
        if policy is None:
            self.goto(self.sign_transaction, save_curr=False)
            return

        from policy_display import compatible_path_indexes
        compatible_sets = []
        for input_index, txin in self.psbt.input_iter():
            plan = self.psbt.inputs[input_index].policy_spend_plan
            if plan and plan.policy_id == policy.policy_id:
                compatible_sets.append(compatible_path_indexes(
                    policy, self.psbt.txn_version, self.psbt.lock_time,
                    txin.nSequence))
        compatible = None
        warning = None
        if not compatible_sets:
            warning = ('Spending paths could not be checked for this transaction. '
                       'The following pages describe the full wallet policy.')
        elif any(not paths for paths in compatible_sets):
            compatible = ()
        elif all(paths == compatible_sets[0] for paths in compatible_sets):
            compatible = compatible_sets[0]
        else:
            warning = 'Inputs allow different spending paths. The following pages describe the full wallet policy.'

        from flows import SeriesOfPagesFlow
        from pages import LongTextPage
        if warning:
            texts = (warning,) + policy.format_review_pages()
        else:
            texts = policy.format_signing_pages(compatible)
        page_args = [{
            'card_header': {'title': 'Policy transaction'},
            'text': text,
            'centered': True,
            'require_scroll_to_end': True,
        } for text in texts]
        result = await SeriesOfPagesFlow(LongTextPage, page_args).run()
        if result:
            self.goto(self.sign_transaction)
        else:
            self.back()

    async def sign_transaction(self):
        from tasks.sign_psbt_task import sign_psbt_task
        from utils import spinner_task
        from pages import ErrorPage, QuestionPage

        gc.collect()

        if self.psbt.active_policy:
            from utils import escape_text
            question = 'Sign with {}?'.format(
                escape_text(self.psbt.active_policy.name))
        else:
            question = 'Sign transaction?'
        result = await QuestionPage(text=question, right_micron=microns.Sign).show()
        if not result:
            should_cancel = await QuestionPage(text='Cancel this transaction?').show()
            if should_cancel:
                self.set_result(None)
            else:
                self.back()
        else:
            (error_msg, error) = await spinner_task('Signing Transaction',
                                                    sign_psbt_task, args=[self.psbt])
            gc.collect()
            if error is not None:
                await self.show_psbt_error(error_msg)
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

        val = ' '.join(self.chain.render_value(o.nValue))
        dest = self.chain.render_address(o.scriptPubKey)

        if dest.startswith("OP_RETURN"):
            # user-defined message starts after "OP_RETURN:\n"
            message = dest.split('\n', 1)[1]
            return '\n{}\n{}\n\n{}\nOP_RETURN\n\n{}\n{}'.format(
                recolor(HIGHLIGHT_TEXT_HEX, 'Amount'),
                val,
                recolor(HIGHLIGHT_TEXT_HEX, 'Destination'),
                recolor(HIGHLIGHT_TEXT_HEX, 'Message'),
                render_op_return_message(message))

        dest = stylize_address(dest)

        return '\n{}\n{}\n\n{}\n{}'.format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Amount'),
            val,
            recolor(HIGHLIGHT_TEXT_HEX, 'Destination'),
            dest)

    def render_change_text(self):
        if not any(output.is_change for output in self.psbt.outputs):
            return 'No change'
        total = sum(output.nValue for index, output in self.psbt.output_iter() if self.psbt.outputs[index].is_change)
        amount = ' '.join(self.chain.render_value(total))
        return '{}\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Change Amount'), amount)

    def invalid_psbt_text(self, exc):
        # Labels render with LVGL recolor on, so a literal '#' in the text opens
        # a colour tag and the characters after it are eaten as a hex code.
        # psbt.py raises plenty of messages shaped like "... for input #3", and
        # the index is the most useful part of them, so escape before display.
        return 'Invalid PSBT: {}'.format(escape_text('{}'.format(exc)))

    def render_fee(self):
        fee = self.psbt.calculate_fee()
        if not self.psbt.fee_is_verified or fee is None:
            amount = 'Unverified'
        else:
            amount = ' '.join(self.chain.render_value(fee))
        return '{}\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Network Fee'), amount)

    def render_warning(self, warning):
        label, message = warning
        return '{}\n{}'.format(recolor(BLACK_HEX, escape_text(label)), escape_text(message))
