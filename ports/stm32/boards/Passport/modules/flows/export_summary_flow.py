# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_summary_flow.py - Flow to export a summary of the current wallet

from flows import Flow


def generate_public_contents():
    from public_constants import AF_CLASSIC
    import chains
    import stash
    from utils import xfp2str
    from common import settings

    # Generate public details about wallet.
    #
    # simple text format:
    #   key = value
    # or #comments
    # but value is JSON

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


class ExportSummaryFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_export, name="ExportSummaryFlow")
        self.error = None
        self.body = generate_public_contents()

    def write_fn(self, filename):
        with open(filename, 'wb') as fd:
            for _idx, part in enumerate(self.body):
                fd.write(part.encode())

    async def confirm_export(self):
        from pages import QuestionPage

        result = await QuestionPage(text='Export wallet info to microSD?').show()
        if result:
            self.goto(self.do_export)
        else:
            self.set_result(False)

    async def do_export(self):
        from flows import SaveToMicroSDFlow

        result = await SaveToMicroSDFlow(filename='public.txt', write_fn=self.write_fn).run()
        self.set_result(result)
