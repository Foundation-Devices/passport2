# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from data_codecs.qr_type import QRType
from flows import Flow
from pages import ScanQRPage, LongErrorPage, ErrorPage
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
                 failure_message=None):
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
        self.failure_message = failure_message or 'Unable to scan QR code.\n\n{}'

        if len(self.qr_types) == 0:
            raise ValueError('At least one QR type must be provided')

        if QRType.UR2 in self.qr_types and len(self.ur_types) == 0:
            raise ValueError('At least one UR type must be provided')

        if self.data_description is None:
            raise ValueError('Data description must be provided')

    async def scan(self):
        from errors import Error

        result = await ScanQRPage(max_frames=self.max_frames,
                                  qr_type=self.explicit_type) \
            .show(auto_close_timeout=self.auto_close_timeout)

        if result is None:
            self.set_result(None)
            return

        if result.is_unsupported():
            await LongErrorPage(text="""Unsupported QR type.

Check for updates to Passport and your software wallet.""").show()
            self.set_result(None)
            return

        if result.is_ur_too_big():
            self.set_result(Error.QR_TOO_LARGE)
            return

        if result.is_failure():
            await LongErrorPage(text=self.failure_message.format(result.error)).show()
            self.set_result(None)
            return

        if result.is_oversized():
            self.set_result(Error.PSBT_OVERSIZED)
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

        if self.data is None:
            await ErrorPage(text='Scan failed.\n'
                                 'No data found in this UR code. Expected '
                                 '{}.'.format(self.data_description)).show()
            self.set_result(None)

        self.set_result(self.data)

    async def handle_qr(self):
        if QRType.QR not in self.qr_types and QRType.QR != self.explicit_type:
            await ErrorPage(text='Scan. failed.\n'
                                 'Expected to scan a Uniform Resource containing '
                                 '{}.'.format(self.data_description)).show()
            self.set_result(None)
            return

        if self.data is None:
            await ErrorPage(text='Scan failed.\n'
                                 'No data found in this QR code. Expected '
                                 '{}.'.format(self.data_description)).show()
            self.set_result(None)

        self.set_result(self.data)
