# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""User-facing PSBT messages kept separate from parser diagnostics."""


def format_psbt_error(message):
    """Return a friendly explanation and, when useful, the original detail."""
    message = str(message or 'Unknown PSBT error')
    lower = message.lower()

    if ('missing redeem/witness script' in lower or
            'need witness script' in lower):
        if 'output' in lower:
            friendly = (
                'This PSBT is missing information Passport needs to verify a change output.\n\n'
                'Re-export it from your wallet coordinator with the complete witness or redeem script.'
            )
        else:
            friendly = (
                'This PSBT is missing information Passport needs to verify how an input can be spent.\n\n'
                'Re-export it from your wallet coordinator with the complete witness or redeem script.'
            )
        return friendly, message

    if 'unknown registered wallet policy' in lower:
        return (
            'Passport cannot match this transaction to a registered wallet policy.\n\n'
            'Register the exact policy used by your wallet coordinator, then try again.',
            message,
        )

    if 'wallet policy change output does not match' in lower:
        return (
            'A change output does not match the registered wallet policy.\n\n'
            'Do not sign. Check the wallet in your coordinator and create the transaction again.',
            message,
        )

    if ('does not match the registered policy' in lower or
            'do not match the registered policy' in lower or
            'registered policy belongs to another seed' in lower or
            'matches multiple wallet policies' in lower):
        return (
            'This transaction does not match the registered wallet policy and Passport key.\n\n'
            'Do not sign. Check the policy in your wallet coordinator and on Passport, then '
            'create the transaction again.',
            message,
        )

    if ('multiple wallet policies' in lower or
            'mix registered wallet policy' in lower or
            'mix legacy multisig and registered wallet policy' in lower):
        return (
            'This transaction combines inputs from incompatible wallet configurations.\n\n'
            'Create a transaction using one registered wallet policy and try again.',
            message,
        )

    if lower.startswith('invalid psbt:'):
        return (
            'Passport could not read this PSBT.\n\n'
            'Create a new PSBT in your wallet coordinator and try again.',
            message,
        )

    return message, None


def format_signed_psbt_message(updated_path, finalized_path=None, txid=None):
    """Explain exactly what Passport produced and what the user should do next."""
    lines = [
        'Passport signature added',
        '',
        'Updated PSBT',
        str(updated_path),
        '',
    ]
    if finalized_path:
        lines.extend([
            'Next step',
            'Return the updated PSBT to your wallet coordinator to finalize and broadcast.',
            '',
            'Passport also saved a finalized transaction that is ready to broadcast.',
            str(finalized_path),
        ])
        if txid:
            lines.extend(['', 'Transaction ID', str(txid)])
    else:
        lines.extend([
            'Next step',
            'Return the updated PSBT to your wallet coordinator to collect any remaining signatures, '
            'finalize, and broadcast.',
        ])
    return '\n'.join(lines)


# nLockTime values at or above this are Unix times; below it, block heights.
LOCKTIME_THRESHOLD = 500000000
SEQUENCE_FINAL = 0xffffffff
# BIP68 relative lock fields of an input's nSequence.
SEQUENCE_DISABLE_FLAG = 1 << 31
SEQUENCE_TYPE_FLAG = 1 << 22
SEQUENCE_VALUE_MASK = 0xffff
SEQUENCE_SECONDS_PER_UNIT = 512


def timelock_warnings(txn_version, lock_time, sequences):
    """Return review warnings for timelocks that delay when the transaction can confirm.

    Wallets routinely set nLockTime to the current block height, and Passport
    doesn't know the current height, so a height lock can't be told apart from
    one far in the future. Only a lock to a date, and a relative lock on an
    input, are flagged: wallets rarely set either.
    """
    warnings = []
    if lock_time >= LOCKTIME_THRESHOLD and any(sequence != SEQUENCE_FINAL for sequence in sequences):
        warnings.append(('Timelock', "This transaction can't be confirmed until after {} UTC.".format(
            format_utc_time(lock_time))))

    # Relative locks apply from version 2 on (BIP68).
    lines = []
    if txn_version >= 2:
        for index, sequence in enumerate(sequences):
            value = sequence & SEQUENCE_VALUE_MASK
            if sequence & SEQUENCE_DISABLE_FLAG or not value:
                continue
            if sequence & SEQUENCE_TYPE_FLAG:
                wait = format_duration(value * SEQUENCE_SECONDS_PER_UNIT)
            else:
                wait = '{} block{}'.format(value, '' if value == 1 else 's')
            lines.append('Input {}: {}'.format(index + 1, wait))
    if lines:
        warnings.append(('Relative Timelock',
                         "This transaction can't be confirmed until these inputs have waited this long "
                         'after they were confirmed:\n\n' + '\n'.join(lines)))
    return warnings


def format_utc_time(timestamp):
    """Format a Unix time as YYYY-MM-DD HH:MM.

    utime counts from 2000 on this port, so the date is computed here
    (Howard Hinnant's civil-from-days).
    """
    days, seconds = divmod(timestamp, 86400)
    days += 719468
    era = days // 146097
    day_of_era = days - era * 146097
    year_of_era = (day_of_era - day_of_era // 1460 + day_of_era // 36524 - day_of_era // 146096) // 365
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    month_index = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * month_index + 2) // 5 + 1
    month = month_index + 3 if month_index < 10 else month_index - 9
    year = year_of_era + era * 400 + (1 if month <= 2 else 0)
    return '{:04d}-{:02d}-{:02d} {:02d}:{:02d}'.format(year, month, day, seconds // 3600, seconds % 3600 // 60)


def format_duration(seconds):
    """Round seconds to the largest whole unit, e.g. 'about 2 days'."""
    for unit, size in (('day', 86400), ('hour', 3600), ('minute', 60)):
        if seconds >= size:
            count = (seconds + size // 2) // size
            return 'about {} {}{}'.format(count, unit, '' if count == 1 else 's')
    return '{} seconds'.format(seconds)
