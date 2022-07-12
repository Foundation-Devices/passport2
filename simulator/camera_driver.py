# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# camera_driver.py = Compatibility layer: emulate a camera by talking to the web cam on the simulator

import sys
import common

CAMERA_WIDTH = 396
CAMERA_HEIGHT = 330
CAMERA_BYTES_PER_PIXEL = 2
CAMERA_IMAGE_SIZE = (CAMERA_WIDTH * CAMERA_HEIGHT * CAMERA_BYTES_PER_PIXEL)


class CameraDriver():
    def __init__(self):
        # TODO: Check the file descriptor - they may not have the right value
        self.cam_cmd_wx = open(int(sys.argv[4]), 'wb')
        self.cam_img_rx = open(int(sys.argv[5]), 'rb')
        # print("cam_cmd_wx=" + str(self.cam_cmd_wx))
        # print("cam_img_rx=" + str(self.cam_img_rx))
        self._is_enabled = False
        # TODO: Could replace this with a statically allocated buffer, but it's probably
        #       fine if we just make sure that this is allocated at startup.
        self.image = bytearray(CAMERA_IMAGE_SIZE)
        # print('====Buffer allocated')

    def __del__(self):
        self.cam_cmd_wx.close()
        self.cam_img_rx.close()

    def is_enabled(self):
        return self._is_enabled

    def enable(self):
        self.cam_cmd_wx.write(b"enable")
        self.active = True
        # print('====Camera enabled')

    def disable(self):
        self.cam_cmd_wx.write(b"disable")
        self.active = False

    def get_image_buffer(self):
        return self.image

    def capture(self, filename=None):
        print('====START CAPTURE')
        # Send the capture command
        self.cam_cmd_wx.write(b"capture")

        # Wait for a frame
        # TODO: NOTE: This is actually blocking...can we make it async?
        bytes_read = self.cam_img_rx.readinto(self.image)
        if bytes_read != CAMERA_IMAGE_SIZE:
            # ERROR: Didn't read an image
            print("$$$$$$$$$$$$$$$$$$$$$$$$ Incorrect image size received")
            return None

        print('====END CAPTURE')
        return self.image
