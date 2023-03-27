# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_to_microsd_flow.py - Save a file to the microSD card

from flows import Flow


class SaveToMicroSDFlow(Flow):
    def __init__(self, filename, data, success_text="file", path=None, mode=''):
        self.filename = filename.replace(' ', '_')
        self.data = data
        self.success_text = success_text
        self.path = path
        self.mode = mode
        self.out_full = None
        super().__init__(initial_state=self.save, name='SaveToMicroSDFlow')

    async def save(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage

        try:
            with CardSlot() as card:
                self.out_full, _ = card.pick_filename(self.filename, self.path)
                with open(self.out_full, 'w' + self.mode) as fd:
                    fd.write(self.data)
        except CardMissingError:
            self.goto(self.show_card_missing)
            return
        except Exception as e:
            await ErrorPage(text='Failed to write file: {}'.format(e)).show()
            self.set_result(False)
            return

        self.goto(self.success)

    async def success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved {} as {}.'.format(self.success_text, self.out_full)).show()
        self.set_result(True)

    async def show_card_missing(self):
        from pages import InsertMicroSDPage

        result = await InsertMicroSDPage().show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.save)
