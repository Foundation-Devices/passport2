# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_text_file_flow.py - Ask user to choose a file from microSD and then sign it.

from files import CardMissingError, CardSlot
from flows import Flow, FilePickerFlow
from pages import SuccessPage, ErrorPage, InsertMicroSDPage
from tasks import sign_text_file_task
from utils import spinner_task, validate_sign_text
from translations import t, T
from public_constants import AF_CLASSIC, MSG_SIGNING_MAX_LENGTH, RFC_SIGNATURE_TEMPLATE
import sys


def is_signable(filename):
    # print('is_signable: {}'.format(filename))
    if '-signed' in filename.lower():
        return False

    return True
    # with open(filename, 'rt') as fd:
    #     lines = fd.readlines()
    #     print('len(lines) = {}'.format(len(lines)))
    #     return (1 <= len(lines) <= 5)


class SignTextFileFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.select_file, name='SignTextFileFlow')

    async def select_file(self):
        result = await FilePickerFlow(title='Choose File to Sign', filter_fn=is_signable).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.validate_file)

    async def validate_file(self):
        from common import system

        with CardSlot() as card:
            with open(self.file_path, 'rb') as fd:
                import os

                s = os.stat(self.file_path)
                self.size = s[6]

                # Check length
                if self.size < 2:
                    await ErrorPage(
                        'File is too short. Must be at least 2 bytes.'.format(MSG_SIGNING_MAX_LENGTH)).show()
                    self.set_result(False)
                    return

                if self.size > MSG_SIGNING_MAX_LENGTH:
                    await ErrorPage(
                        'File is too long. Max. length is {} bytes.'.format(MSG_SIGNING_MAX_LENGTH)).show()
                    self.set_result(False)
                    return

                # Read the file
                self.text = fd.readline().strip().decode('utf-8')

                self.subpath = fd.readline().strip().decode('utf-8')

                # Validate
                (subpath, error) = validate_sign_text(self.text, self.subpath)
                if error is not None:
                    await ErrorPage(text=error).show()
                    self.set_result(False)
                    return

                self.subpath = subpath

                # All looks good so far, so try to sign it
                self.goto(self.do_sign)

    async def do_sign(self):
        (signature, address, error) = await spinner_task('Signing File', sign_text_file_task,
                                                         args=[self.text, self.subpath, AF_CLASSIC])
        if error is None:
            self.signature = signature
            self.address = address
            self.goto(self.write_signed_file)
        else:
            # TODO: Refactor this to a simpler, common error handler page?
            await ErrorPage(text='Error while signing file: {}'.format(error)).show()
            self.set_result(False)
            return

    # TODO: Should this logic be in a task?  It's pretty fast, but should probably at least be a function for
    #       unit test purposes.
    async def write_signed_file(self):
        # complete. write out result
        from ubinascii import b2a_base64
        orig_path, basename = self.file_path.rsplit('/', 1)
        orig_path += '/'
        base = basename.rsplit('.', 1)[0]
        out_fn = None

        sig = b2a_base64(self.signature).decode('ascii').strip()

        while 1:
            # try to put back into same spot
            # add -signed to end.
            target_fname = base + '-signed.txt'

            for path in [orig_path, None]:
                try:
                    with CardSlot() as card:
                        out_full, out_fn = card.pick_filename(
                            target_fname, path)
                        out_path = path
                        if out_full:
                            break
                except CardMissingError:
                    prob = 'Missing card.\n\n'
                    out_fn = None

            if not out_fn:
                # need them to insert a card
                prob = ''
            else:
                # attempt write-out
                try:
                    with CardSlot() as card:
                        with open(out_full, 'wt') as fd:
                            # save in full RFC style
                            fd.write(RFC_SIGNATURE_TEMPLATE.format(addr=self.address, msg=self.text,
                                                                   blockchain='BITCOIN', sig=sig))

                    # success and done!
                    break

                except OSError as exc:
                    prob = 'Unable to write!\n\n%s\n\n' % exc
                    sys.print_exception(exc)
                    # fall thru to try again

            # prompt them to input another card?
            result = await InsertMicroSDPage()
            if not result:
                # Give up
                self.set_result(False)
                return

        # Done
        await SuccessPage(text='Signed filename:\n\n{}'.format(out_fn)).show()
        self.set_result(True)
