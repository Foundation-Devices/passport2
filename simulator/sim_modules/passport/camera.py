# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys

HOR_RES = 416
VER_RES = 312
FRAMEBUFFER_SIZE = HOR_RES * VER_RES * 2

cam_cmd_wx = open(int(sys.argv[4]), 'wb')
cam_img_rx = open(int(sys.argv[5]), 'rb')
_framebuffer = bytearray(FRAMEBUFFER_SIZE)
is_enabled = False


def enable():
    """Enable the simulator camera"""
    global cam_cmd_wx, is_enabled

    # print("cam_cmd_wx={}".format(str(cam_cmd_wx)))
    # print("cam_img_rx={}".format(str(cam_img_rx)))

    is_enabled = True
    cam_cmd_wx.write(b"enable\n")


def disable():
    """Disable the simulator camera"""
    global cam_cmd_wx, is_enabled

    is_enabled = False
    cam_cmd_wx.write(b"disable\n")


def snapshot():
    """Take an snapshot of the camera"""

    global cam_cmd_wx, cam_img_rx, _framebuffer, is_enabled

    # Wait for a frame
    if is_enabled:
        # Send the capture command
        cam_cmd_wx.write(b"capture\n")

        bytes_read = cam_img_rx.readinto(_framebuffer)
        if bytes_read != FRAMEBUFFER_SIZE:
            raise RuntimeError("Incorrect image size received: {}".format(bytes_read))


def resize(new_hor_res, new_ver_res):
    global _framebuffer, HOR_RES, VER_RES

    old_hor_res = HOR_RES
    old_ver_res = VER_RES

    y_ratio = ((old_ver_res << 16) // new_ver_res) + 1
    x_ratio = ((old_hor_res << 16) // new_hor_res) + 1

    # For uniform scaling, we need the ratios to be the same, but to avoid out-of-bounds index
    # access on the arrays, we need to take the smaller ratio
    # TODO: add an offset in the smaller direction to center the part we take?
    # TODO: There is a vertical line down the right side of the camera image which is related to the OmniVision
    #       Camera Cube settings.  We haven't been able to find a configuration that avoids this, even in
    #       consultation with OmniVision engineers.
    #
    #       Might want to try with a square resolution to see if it helps, but then should make the onscreen
    #       viewport a square too.
    x_ratio = min(x_ratio, y_ratio)
    y_ratio = x_ratio

    for dst_y in range(new_ver_res):
        for dst_x in range(new_hor_res):
            src_x = (dst_x * x_ratio) >> 16
            src_y = (dst_y * y_ratio) >> 16

            src_pixel = (src_y * old_hor_res * 2) + (src_x * 2)
            dst_pixel = (dst_y * new_hor_res * 2) + (dst_x * 2)

            _framebuffer[dst_pixel + 0] = _framebuffer[src_pixel + 0]
            _framebuffer[dst_pixel + 1] = _framebuffer[src_pixel + 1]


def framebuffer():
    """Returns the framebuffer of the camera"""

    global is_enabled, _framebuffer
    if not is_enabled:
        raise RuntimeError("Camera is disabled")

    return _framebuffer
