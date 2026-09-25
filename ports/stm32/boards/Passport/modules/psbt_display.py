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
