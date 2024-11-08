# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
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
                 automatic=False,
                 auto_prompt=None):
        import microns
        from utils import bind, show_card_missing

        self.filename = filename.replace(' ', '_')
        self.data = data
        self.write_fn = write_fn
        self.success_text = success_text
        self.path = path
        self.mode = mode
        self.out_full = None
        # If auto_prompt isn't specified, use automatic value
        auto_prompt = auto_prompt or automatic
        self.auto_timeout = 1000 if auto_prompt else None
        self.show_check = None if auto_prompt else microns.Checkmark

        # Used in flow_show_card_missing
        self.automatic = automatic
        self.return_bool = False

        bind(self, show_card_missing)

        super().__init__(initial_state=self.check_inputs,
                         name='SaveToMicroSDFlow')

    def default_write_fn(self, filename):
        with open(self.out_full, 'w' + self.mode) as fd:
            fd.write(self.data)

    async def check_inputs(self):
        from pages import ErrorPage

        if (not self.data and not self.write_fn) or (self.data and self.write_fn):
            await ErrorPage("Either data or a write function is required to save a file.").show()
            self.set_result(None)
            return

        self.goto(self.save)

    async def save(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage
        from utils import spinner_task, ensure_folder_exists
        from errors import Error
        from tasks import custom_microsd_write_task

        if self.data:
            self.write_fn = self.default_write_fn

        written = False

        for path in [self.path, None]:
            try:
                with CardSlot() as card:
                    ensure_folder_exists(self.path)
                    self.out_full, _ = card.pick_filename(self.filename, path)
                    error = await spinner_task("Writing {}".format(self.success_text),
                                               custom_microsd_write_task,
                                               args=[self.out_full, self.write_fn])
                    if error is Error.MICROSD_CARD_MISSING:
                        raise CardMissingError()
                    elif error is Error.FILE_WRITE_ERROR:
                        raise Exception("write task failed")
                    written = True
                    break

            except CardMissingError:
                self.goto(self.show_card_missing)
                return

            except Exception as e:
                await ErrorPage(text='Failed to write file: {}'.format(e),
                                right_micron=self.show_check) \
                    .show(auto_close_timeout=self.auto_timeout)
                self.set_result(None)
                return

        if written:
            self.goto(self.success)
        else:
            await ErrorPage("Failed to write file.",
                            right_micron=self.show_check) \
                .show(auto_close_timeout=self.auto_timeout)

    async def success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved {} as {}'.format(self.success_text, self.out_full),
                          right_micron=self.show_check) \
            .show(auto_close_timeout=self.auto_timeout)
        self.set_result(self.out_full)
