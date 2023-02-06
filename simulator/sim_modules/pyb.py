# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

class SDCard:
    ejected = False

    @classmethod
    def present(cls):
        if cls.ejected:
            return False
        SDCard.power(1)
        return True

    @classmethod
    def power(cls, st=0):
        return False


class Pin:
    PULL_NONE = 1
    PULL_UP = 2

    def __init__(self, *a, **kw):
        return


class ExtInt:
    IRQ_RISING = 1
    IRQ_FALLING = 2
    IRQ_RISING_FALLING = 3

    def __init__(self, *a, **kw):
        return
