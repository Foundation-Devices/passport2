# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Entering the last word offers to generate it only for a BIP-39 seed. A six-word backup password has no
# checksum word, and choosing that option would return only five words.

from pages.predictive_text_input_page import PredictiveTextInputPage, RANDOM_WORD_STRING


class Container:
    def add_child(self, item):
        pass


class LastWordEntry:
    def __init__(self, word_list, total_words):
        self.word_list = word_list
        self.total_words = total_words
        self.word_idx = total_words - 1
        self.initial_prefix = ''
        self.prefixes = []
        self.predictions = []
        self.prediction_idx = 0
        self.predictions_container = Container()

    def is_mounted(self):
        return False


seed = LastWordEntry('bip39', 12)
PredictiveTextInputPage.update_predictions(seed)
assert seed.predictions == [RANDOM_WORD_STRING]

backup_password = LastWordEntry('bytewords', 6)
PredictiveTextInputPage.update_predictions(backup_password)
assert backup_password.predictions == []

return_value.write(b'OK')
