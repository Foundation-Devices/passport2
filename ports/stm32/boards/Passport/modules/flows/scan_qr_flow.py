# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from data_codecs.qr_type import QRType
from flows import Flow
from pages import ScanQRPage, ErrorPage
from foundation import ur


class ScanQRFlow(Flow):
    """Flow to scan a QR code or animated QR codes"""

    def __init__(self,
                 auto_close_timeout=None,
                 qr_types=None,
                 ur_types=None,
                 explicit_type=None,
                 data_description=None,
                 max_frames=None,
                 max_frames_text=None):
        """
        Initialize the scan QR flow.

        :param auto_close_timeout: Timeout in seconds for the flow to
        automatically close when nothing is scanned.
        :param qr_types: List of supported QR types.
        :param ur_types: List of supported UR types.
        :raises ValueError: qr_types is provided but empty.
        :raises ValueError: data_description is not provided.
        """
        super().__init__(initial_state=self.scan, name='ScanQRFlow')

        self.auto_close_timeout = auto_close_timeout

        if explicit_type is not None and (qr_types is not None or ur_types is not None):
            raise ValueError('No QR or UR types may be provided along with an explicit type')

        self.qr_types = [QRType.QR] if qr_types is None else qr_types
        self.ur_types = [] if ur_types is None else ur_types
        self.explicit_type = explicit_type
        self.data_description = data_description
        self.data = None
        self.max_frames = max_frames
        self.max_frames_text = max_frames_text

        if len(self.qr_types) == 0:
            raise ValueError('At least one QR type must be provided')

        if QRType.UR2 in self.qr_types and len(self.ur_types) == 0:
            raise ValueError('At least one UR type must be provided')

        if self.data_description is None:
            raise ValueError('Data description must be provided')

    async def scan(self):
        from pages import LongTextPage
        import microns

        result = await ScanQRPage(max_frames=self.max_frames,
                                  qr_type=self.explicit_type) \
            .show(auto_close_timeout=self.auto_close_timeout)

        if result is None:
            self.set_result(None)
            return

        if result.is_failure():
            await ErrorPage(text='Unable to scan QR code.\n\n{}'.format(result.error)).show()
            self.set_result(None)
            return

        if result.is_too_large():
            result = await LongTextPage(text=self.max_frames_text,
                                        centered=True,
                                        left_micron=microns.Cancel,
                                        right_micron=microns.Checkmark).show()

            if result:
                self.set_result(None)
            else:
                self.max_frames = None
            return

        self.data = result.data
        if isinstance(self.data, ur.Value):
            self.goto(self.handle_ur)
        else:
            self.goto(self.handle_qr)

    async def handle_ur(self):
        if QRType.UR2 not in self.qr_types and QRType.UR2 != self.explicit_type:
            await ErrorPage(text='Scan failed.\n'
                                 'Expected to scan a QR code containing '
                                 '{}.'.format(self.data_description)).show()
            self.set_result(None)
            return

        if self.data.ur_type() not in self.ur_types and self.data.ur_type() != self.explicit_type:
            await ErrorPage(text='Scan failed.\n'
                                 'This type of UR is not expected in this context. '
                                 '{}.'.format(self.data_description)).show()

            self.set_result(None)
            return

        self.set_result(self.data)

    async def handle_qr(self):
        if QRType.QR not in self.qr_types and QRType.QR != self.explicit_type:
            await ErrorPage(text='Scan. failed.\n'
                                 'Expected to scan a Uniform Resource containing '
                                 '{}.'.format(self.data_description)).show()
            self.set_result(None)
            return

        self.set_result(self.data)
