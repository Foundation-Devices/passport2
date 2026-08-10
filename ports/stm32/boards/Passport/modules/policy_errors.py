# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later


class WalletPolicyError(ValueError):
    """Base class for policy failures that are safe to show to the user."""

    def __init__(self, code, message, position=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.position = position

    def __str__(self):
        if self.position is None:
            return self.message
        return '{} at character {}'.format(self.message, self.position)


class PolicyParseError(WalletPolicyError):
    def __init__(self, message, position=None):
        super().__init__('parse_error', message, position)


class PolicyTypeError(WalletPolicyError):
    def __init__(self, message):
        super().__init__('type_error', message)


class UnsupportedPolicyError(WalletPolicyError):
    def __init__(self, message):
        super().__init__('unsupported_policy', message)


class PolicyResourceError(WalletPolicyError):
    def __init__(self, message):
        super().__init__('resource_limit', message)


class PolicyMismatchError(WalletPolicyError):
    def __init__(self, message):
        super().__init__('policy_mismatch', message)
