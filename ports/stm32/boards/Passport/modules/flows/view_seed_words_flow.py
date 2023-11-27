# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

from flows import Flow


class ViewSeedWordsFlow(Flow):
    def __init__(self,
                 external_key=None,
                 qr_option=False,
                 sd_option=False,
                 path=None,
                 filename=None,
                 initial=False,
                 allow_skip=True,
                 qr_button=False,
                 key_manager=False):
        import microns

        self.external_key = external_key
        self.qr_option = qr_option

        if sd_option:
            filename = filename or 'Seed.txt'  # Caller should never let this happen

        self.sd_option = sd_option
        self.path = path
        self.filename = filename
        self.qr_type = None
        self.words = None
        self.seed_micron = None if not qr_button else microns.ScanQR
        self.mention_passphrase = True if not external_key else False
        self.initial = initial
        self.allow_skip = allow_skip
        self.use_qr_button = qr_button
        self.seen_warning = False
        self.qr_mode = None
        self.key_manager = key_manager
        super().__init__(initial_state=self.generate_words, name='ViewSeedWordsFlow')

    async def generate_words(self):
        from flows import GetSeedWordsFlow

        self.words = await GetSeedWordsFlow(self.external_key).run()

        if self.words is None:
            self.set_result(False)
            return

        self.goto(self.choose_mode)

    async def choose_mode(self):
        from pages import ChooserPage
        from data_codecs.qr_type import QRType
        import microns

        if not (self.qr_option or self.sd_option):
            self.goto(self.show_seed_words)
            return

        options = [{'label': 'Seed Words', 'value': self.show_seed_words}]

        if self.qr_option:
            options.extend([{'label': 'Compact SeedQR',
                             'value': QRType.COMPACT_SEED_QR},
                            {'label': 'SeedQR',
                             'value': QRType.SEED_QR}])

        if self.sd_option:
            options.append({'label': 'microSD',
                            'value': self.save_to_sd})

        mode = await ChooserPage(card_header={'title': 'Format'}, options=options).show()

        if mode is None:
            self.set_result(False)
            return

        if isinstance(mode, int) and mode in [QRType.SEED_QR, QRType.COMPACT_SEED_QR]:
            self.qr_type = mode
            mode = self.show_qr
            self.seed_micron = microns.Back

        self.goto(mode)

    async def show_qr(self):
        from flows import SeedWarningFlow
        from pages import ShowQRPage
        import microns

        result = await SeedWarningFlow(action_text="display your seed as a QR code",
                                       mention_passphrase=self.mention_passphrase,
                                       initial=self.initial,
                                       allow_skip=self.allow_skip,
                                       key_manager=self.key_manager).run()

        if not result:
            self.back()
            return

        self.seen_warning = True
        result = await ShowQRPage(qr_type=self.qr_type, qr_data=self.words, right_micron=microns.Checkmark).show()

        if not result:
            return

        self.goto(self.confirm_qr)

    async def confirm_qr(self):
        from pages import InfoPage
        import microns

        plural_label = 's' if len(self.words) == 24 else ''
        text = 'Confirm the seed words in the following page{}.'.format(plural_label)
        result = await InfoPage(text=text, left_micron=microns.Back).show()

        if not result:
            self.back()
            return

        self.goto(self.show_seed_words)

    async def save_to_sd(self):
        from flows import SeedWarningFlow
        from utils import B2A
        from flows import SaveToMicroSDFlow

        result = await SeedWarningFlow(action_text="copy your seed to the microSD card",
                                       mention_passphrase=self.mention_passphrase,
                                       initial=self.initial,
                                       allow_skip=self.allow_skip,
                                       key_manager=self.key_manager).run()

        if not result:
            self.back()
            return

        self.seen_warning = True
        text = " ".join(self.words)
        result = await SaveToMicroSDFlow(filename=self.filename,
                                         path=self.path,
                                         data=text,
                                         success_text="seed").run()

        if not result:
            return

        self.goto(self.show_passphrase)

    async def show_seed_words(self):
        from flows import SeedWarningFlow
        from pages import SeedWordsListPage

        if not self.seen_warning:  # We already gave the seed warning flow
            result = await SeedWarningFlow(mention_passphrase=self.mention_passphrase,
                                           initial=self.initial,
                                           allow_skip=self.allow_skip,
                                           key_manager=self.key_manager).run()

            if not result:
                self.set_result(False)
                return

            self.seen_warning = True

        result = False
        while not result:
            result = await SeedWordsListPage(words=self.words,
                                             left_micron=self.seed_micron).show()
            if not result:

                if self.qr_type:
                    self.back()
                    return

                if self.use_qr_button:
                    self.goto(self.qr_intro)
                    return

        self.goto(self.show_passphrase)

    async def qr_intro(self):
        from pages import InfoPage, ChooserPage
        import microns
        from data_codecs.qr_type import QRType

        options = [{'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                   {'label': 'SeedQR', 'value': QRType.SEED_QR}]

        self.qr_mode = await ChooserPage(card_header={'title': 'Format'}, options=options).show()

        if self.qr_mode is None:
            self.back()
            return

        result = await InfoPage('The following QR code contains your seed words.\n\n'
                                'NEVER scan it from an Internet connected device.',
                                left_micron=microns.Back).show()

        if not result:
            return

        self.goto(self.qr_button)

    async def qr_button(self):
        from pages import ShowQRPage
        from data_codecs.qr_type import QRType
        import microns

        result = await ShowQRPage(qr_type=self.qr_mode,
                                  qr_data=self.words,
                                  left_micron=microns.Back,
                                  right_micron=microns.Checkmark).show()

        if not result:
            self.back()
            return

        self.set_result(True)

    async def show_passphrase(self):
        import stash
        from pages import InfoPage

        if stash.bip39_passphrase != '' and not self.external_key:
            await InfoPage(text='Passphrase: {}'.format(stash.bip39_passphrase)).show()
        self.set_result(True)
