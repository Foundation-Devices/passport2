# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# test_microsd_flow.py - Tests SD card by writing and reading a test file

from flows import Flow
from pages import SuccessPage, ErrorPage, InsertMicroSDPage


class TestMicroSDFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.write_and_read_file, name='TestMicrosdFlow')

    async def write_and_read_file(self):
        import os
        from files import CardSlot, CardMissingError
        from utils import file_exists

        while True:
            msg = 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks'

            try:
                with CardSlot() as card:
                    filename = '{}/microsd-test.txt'.format(card.get_sd_root())

                    if file_exists(filename):
                        os.remove(filename)

                    with open(filename, 'wt') as fd:
                        fd.write(msg)

                    with open(filename, 'rt') as fd:
                        read_msg = fd.read()
                        os.remove(filename)

                        if read_msg == msg:
                            # Done
                            await SuccessPage(text='The microSD test passed.').show()
                            self.set_result(True)
                            return
                        else:
                            await ErrorPage(
                                'Wrong text read from microSD card:\n\n {}'.format(
                                    read_msg)).show()
                            self.set_result(False)
                            return

            except CardMissingError:
                result = await InsertMicroSDPage().show()
                if not result:
                    self.set_result(False)
                    return
                else:
                    continue

            except Exception as e:
                await ErrorPage(text='Exception: {}'.format(e)).show()
                self.set_result(False)
                return
