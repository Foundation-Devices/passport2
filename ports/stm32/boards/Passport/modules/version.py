# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# version.py - Compare simple version numbers


class Version:
    """Simple version comparison class"""

    def __init__(self, vstring=None):
        if vstring:
            self.parse(vstring)

    def __repr__(self):
        return "%s ('%s')" % (self.__class__.__name__, str(self))

    def __eq__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c == 0

    def __lt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c < 0

    def __le__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c <= 0

    def __gt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c > 0

    def __ge__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c >= 0

    def major_version(self):
        return self.version[0]

    def minor_version(self):
        return self.version[1]

    def patch_version(self):
        return self.version[2]

    def parse(self, vstring):
        parts = vstring.split('.')
        self.version = tuple(map(int, parts))

    def __str__(self):
        return '.'.join(map(str, self.version))

    def _cmp(self, other):
        if isinstance(other, str):
            other = Version(other)
        elif not isinstance(other, Version):
            return NotImplemented

        if self.version == other.version:
            return 0

        # numeric versions don't match
        if self.version < other.version:
            return -1
        else:
            return 1
