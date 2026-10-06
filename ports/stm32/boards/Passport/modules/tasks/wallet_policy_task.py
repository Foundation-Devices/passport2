# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later


async def save_wallet_policy_task(on_done, policy):
    from common import settings
    from errors import Error
    from ext_settings import SettingsOutOfSpace
    from wallet_policy import POLICY_STORAGE_KEY, WalletPolicyRegistry

    original = list(settings.get(POLICY_STORAGE_KEY, []))
    try:
        WalletPolicyRegistry(settings).save(policy)
        settings.save()
    except BaseException as exc:
        try:
            settings.set(POLICY_STORAGE_KEY, original)
            settings.save()
        except BaseException:
            pass
        error = Error.USER_SETTINGS_FULL if isinstance(exc, SettingsOutOfSpace) else Error.USER_SETTINGS_SAVE_FAILED
        await on_done(error)
        return
    await on_done(None)


async def delete_wallet_policy_task(on_done, policy_id):
    from common import settings
    from errors import Error
    from ext_settings import SettingsOutOfSpace
    from wallet_policy import POLICY_STORAGE_KEY, WalletPolicyRegistry

    original = list(settings.get(POLICY_STORAGE_KEY, []))
    try:
        registry = WalletPolicyRegistry(settings)
        if registry.get(policy_id) is None:
            raise ValueError('Wallet policy not found')
        registry.delete(policy_id)
        settings.save()
    except BaseException as exc:
        try:
            settings.set(POLICY_STORAGE_KEY, original)
            settings.save()
        except BaseException:
            pass
        error = Error.USER_SETTINGS_FULL if isinstance(exc, SettingsOutOfSpace) else Error.USER_SETTINGS_SAVE_FAILED
        await on_done(error)
        return
    await on_done(None)


async def rename_wallet_policy_task(on_done, policy_id, name):
    from common import settings
    from errors import Error
    from ext_settings import SettingsOutOfSpace
    from wallet_policy import POLICY_STORAGE_KEY, WalletPolicyRegistry

    original = list(settings.get(POLICY_STORAGE_KEY, []))
    try:
        WalletPolicyRegistry(settings).rename(policy_id, name)
        settings.save()
    except BaseException as exc:
        try:
            settings.set(POLICY_STORAGE_KEY, original)
            settings.save()
        except BaseException:
            pass
        error = Error.USER_SETTINGS_FULL if isinstance(exc, SettingsOutOfSpace) else Error.USER_SETTINGS_SAVE_FAILED
        await on_done(error)
        return
    await on_done(None)


async def rename_wallet_policy_keys_task(on_done, policy_id, names):
    from common import settings
    from errors import Error
    from ext_settings import SettingsOutOfSpace
    from wallet_policy import POLICY_STORAGE_KEY, WalletPolicyRegistry

    original = list(settings.get(POLICY_STORAGE_KEY, []))
    try:
        WalletPolicyRegistry(settings).rename_keys(policy_id, names)
        settings.save()
    except BaseException as exc:
        try:
            settings.set(POLICY_STORAGE_KEY, original)
            settings.save()
        except BaseException:
            pass
        error = Error.USER_SETTINGS_FULL if isinstance(exc, SettingsOutOfSpace) else Error.USER_SETTINGS_SAVE_FAILED
        await on_done(error)
        return
    await on_done(None)
