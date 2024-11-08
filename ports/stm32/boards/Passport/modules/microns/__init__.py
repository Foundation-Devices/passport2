# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# __init__.py

import lvgl as lv
from styles.colors import FD_BLUE, MICRON_GREY
from views import IconButton, Icon


def Checkmark(color=FD_BLUE):
    return IconButton(icon=lv.ICON_CHECKMARK, color=color)


def Cancel(color=MICRON_GREY):
    return IconButton(icon=lv.ICON_CANCEL, color=color)


def Forward(color=FD_BLUE):
    return IconButton(icon=lv.ICON_FORWARD, color=color)


def Back(color=MICRON_GREY):
    return IconButton(icon=lv.ICON_BACK, color=color)


def Shutdown(color=MICRON_GREY):
    return IconButton(icon=lv.ICON_SHUTDOWN, color=color)


def Sign(color=FD_BLUE):
    return IconButton(icon=lv.ICON_SIGN, color=color)


def Retry(color=FD_BLUE):
    return IconButton(icon=lv.ICON_RETRY, color=color)


def MicroSD(color=FD_BLUE):
    return IconButton(icon=lv.ICON_MICROSD, color=color)


def ScanQR(color=FD_BLUE):
    return IconButton(icon=lv.ICON_SCAN_QR, color=color)


def PageHome(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_HOME, color=color)


def PageDot(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_DOT, color=color)


def PagePlus(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_PLUS, color=color)


def PageQRSmall(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_QR_SM, color=color)


def PageQRMedium(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_QR_MD, color=color)


def PageQRLarge(color=MICRON_GREY):
    return Icon(icon=lv.ICON_PAGE_QR_LG, color=color)
