# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# export_summary_task.py - Task to export a summary of wallet details to file.


from files import CardSlot, CardMissingError
from uasyncio import sleep_ms
from public_constants import AF_CLASSIC
import chains
import stash
from utils import xfp2str
from errors import Error


def generate_public_contents():
    # Generate public details about wallet.
    #
    # simple text format:
    #   key = value
    # or #comments
    # but value is JSON
    from common import settings

    num_rx = 5

    chain = chains.current_chain()

    with stash.SensitiveValues() as sv:

        yield ('''\
# Passport Summary File
## For wallet with master key fingerprint: {xfp}

Wallet operates on blockchain: {nb}

For BIP44, this is coin_type '{ct}', and internally we use
symbol {sym} for this blockchain.

## IMPORTANT WARNING

Do **not** deposit to any address in this file unless you have a working
wallet system that is ready to handle the funds at that address!

## Top-level, 'master' extended public key ('m/'):

{xpub}

What follows are derived public keys and payment addresses, as may
be needed for different systems.
'''.format(nb=chain.name, xpub=chain.serialize_public(sv.node),
           sym=chain.ctype, ct=chain.b44_cointype, xfp=xfp2str(sv.node.my_fingerprint())))

        for name, path, addr_fmt in chains.CommonDerivations:

            if '{coin_type}' in path:
                path = path.replace('{coin_type}', str(chain.b44_cointype))

            if '{' in name:
                name = name.format(core_name=chain.core_name)

            show_slip132 = ('Core' not in name)

            yield ('''## For {name}: {path}\n\n'''.format(name=name, path=path))
            yield ('''First %d receive addresses (account=0, change=0):\n\n''' % num_rx)

            submaster = None
            for i in range(num_rx):
                subpath = path.format(account=0, change=0, idx=i)

                # find the prefix of the path that is hardneded
                if "'" in subpath:
                    hard_sub = subpath.rsplit("'", 1)[0] + "'"
                else:
                    hard_sub = 'm'

                if hard_sub != submaster:
                    # dump the xpub needed

                    if submaster:
                        yield "\n"

                    node = sv.derive_path(hard_sub, register=False)
                    yield ("%s => %s\n" % (hard_sub, chain.serialize_public(node)))
                    if show_slip132 and addr_fmt != AF_CLASSIC and (addr_fmt in chain.slip132):
                        yield ("%s => %s   ##SLIP-132##\n" % (
                            hard_sub, chain.serialize_public(node, addr_fmt)))

                    submaster = hard_sub
                    # TODO: Add blank() back into trezor?
                    # node.blank()
                    del node

                # show the payment address
                node = sv.derive_path(subpath, register=False)
                yield ('%s => %s\n' % (subpath, chain.address(node, addr_fmt)))

                # TODO: Do we need to do this? node.blank()
                del node

            yield ('\n\n')

    # from multisig import MultisigWallet
    # if MultisigWallet.exists():
    #     yield '\n# Your Multisig Wallets\n\n'
    #     from uio import StringIO
    #
    #     for ms in MultisigWallet.get_all():
    #         fp = StringIO()
    #
    #         ms.render_export(fp)
    #         print("\n---\n", file=fp)
    #
    #         yield fp.getvalue()
    #         del fp


async def export_summary_task(on_done, filename_pattern):
    # Generator function
    body = generate_public_contents()

    try:
        with CardSlot() as card:
            # Choose a unique filename
            fname, nice = card.pick_filename(filename_pattern)

            # Do actual write
            with open(fname, 'wb') as fd:
                for _idx, part in enumerate(body):
                    fd.write(part.encode())
                    await sleep_ms(1)

    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        return
    except Exception as e:
        await on_done(Error.FILE_WRITE_ERROR)
        return

    await on_done(None)
