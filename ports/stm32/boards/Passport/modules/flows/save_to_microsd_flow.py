# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_to_microsd_flow.py - Save a file to the microSD card

from flows import Flow


class SaveToMicroSDFlow(Flow):
    def __init__(self,
                 filename,
                 data=None,
                 write_fn=None,  # Custom function for writing, used instead of data
                 success_text="file",
                 path=None,
                 mode='',
                 automatic=False):
        import microns

        self.filename = filename.replace(' ', '_')
        self.data = data
        self.write_fn = write_fn
        self.success_text = success_text
        self.path = path
        self.mode = mode
        self.out_full = None
        self.automatic = automatic
        self.auto_timeout = 1000 if automatic else None
        self.show_check = None if automatic else microns.Checkmark
        # return_bool attribute required to use show_card_missing
        self.return_bool = True
        super().__init__(initial_state=self.save, name='SaveToMicroSDFlow')

    async def save(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage
        from utils import spinner_task, ensure_folder_exists
        from errors import Error
        from tasks import custom_microsd_write_task

        written = False

        for path in [self.path, None]:
            try:
                with CardSlot() as card:
                    ensure_folder_exists(self.path)

                    self.out_full, _ = card.pick_filename(self.filename, path)

                    if self.data:
                        with open(self.out_full, 'w' + self.mode) as fd:
                            fd.write(self.data)
                        written = True
                    elif self.write_fn:
                        error = await spinner_task("Writing {}".format(self.success_text),
                                                   custom_microsd_write_task,
                                                   args=[self.out_full, self.write_fn])
                        if error is Error.MICROSD_CARD_MISSING:
                            raise CardMissingError()
                        elif error is Error.FILE_WRITE_ERROR:
                            raise Exception("write task failed")
                        written = True
                    if written:
                        break

            except CardMissingError:
                # show_card_missing is a global flow state
                self.goto(self.show_card_missing)
                return

            except Exception as e:
                await ErrorPage(text='Failed to write file: {}'.format(e),
                                right_micron=self.show_check) \
                    .show(auto_close_timeout=self.auto_timeout)
                self.set_result(False)
                return

        if written:
            self.goto(self.success)
        else:
            await ErrorPage("Failed to write file: no data or write task.",
                            right_micron=self.show_check) \
                .show(auto_close_timeout=self.auto_timeout)

    async def success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved {} as {}'.format(self.success_text, self.out_full),
                          right_micron=self.show_check) \
            .show(auto_close_timeout=self.auto_timeout)
        self.set_result(True)
