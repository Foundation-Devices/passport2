# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# health_check_flow.py - Scan and process a health check QR code in `crypto-request` format

from flows import Flow


def is_health_check(filename, path=None):
    filename = filename.lower()

    if '-signed' in filename:
        return False

    if '-hc' in filename:
        return True
    return False


class HealthCheckMicrosdFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.choose_file, name='HealthCheckMicrosdFlow')
        self.file_path = None
        self.lines = None
        self.signed_message = None
        self.service_name = context

    async def choose_file(self):
        from flows import FilePickerFlow

        result = await FilePickerFlow(show_folders=True, filter_fn=is_health_check).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.parse_message)

    async def parse_message(self):
        from flows import ReadFileFlow

        data = await ReadFileFlow(self.file_path, binary=False).run()

        if not data:
            self.set_result(False)
            return

        self.lines = data.split('\n')
        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import HealthCheckCommonFlow

        self.signed_message = await HealthCheckCommonFlow(self.lines).run()
        if self.signed_message is None:
            self.set_result(False)
            return
        self.goto(self.write_signed_file)

    async def write_signed_file(self):
        from flows import SaveToMicroSDFlow

        orig_path, basename = self.file_path.rsplit('/', 1)
        base, ext = basename.rsplit('.', 1)
        filename = base + '-signed' + '.' + ext
        result = await SaveToMicroSDFlow(filename=filename,
                                         data=self.signed_message,
                                         success_text="updated health check",
                                         path=orig_path).run()
        self.set_result(result)
