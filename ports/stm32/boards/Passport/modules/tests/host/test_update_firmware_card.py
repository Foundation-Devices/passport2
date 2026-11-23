# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: a missing card or unreadable file while showing update details."""

import asyncio
import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]


class CardMissingError(RuntimeError):
    pass


@pytest.fixture
def flow(monkeypatch):
    events = []
    card = {'missing': True, 'insert': False}

    class CardSlot:
        def __enter__(self):
            if card['missing']:
                raise CardMissingError()
            return self

        def __exit__(self, *args):
            return False

    class Page:
        def __init__(self, *args, text=None, **kwargs):
            self.text = text if text is not None else (args[0] if args else None)

        async def show(self):
            events.append((type(self).__name__, self.text))
            return card['insert']

    pages = types.SimpleNamespace(**{name: type(name, (Page,), {}) for name in (
        'ErrorPage', 'ProgressPage', 'QuestionPage', 'SuccessPage', 'InsertMicroSDPage', 'InfoPage')})

    class Flow:
        def __init__(self, **kwargs):
            pass

    stubs = {
        'lvgl': types.SimpleNamespace(),
        'machine': types.SimpleNamespace(),
        'files': types.SimpleNamespace(CardSlot=CardSlot, CardMissingError=CardMissingError),
        'constants': types.SimpleNamespace(FW_HEADER_SIZE=2048, FW_MAX_SIZE=2000000),
        'pages': pages,
        'tasks': types.SimpleNamespace(verify_firmware_signature_task=None, copy_firmware_to_spi_flash_task=None),
        'flows': types.SimpleNamespace(Flow=Flow, FilePickerFlow=None),
        'utils': types.SimpleNamespace(read_user_firmware_pubkey=None, is_all_zero=None, start_task=None),
        'errors': types.SimpleNamespace(Error=None),
        'passport': types.SimpleNamespace(),
        'common': types.SimpleNamespace(),
    }
    for name, stub in stubs.items():
        monkeypatch.setitem(sys.modules, name, stub)

    flow_class = runpy.run_path(str(MODULES / 'flows/update_firmware_flow.py'))['UpdateFirmwareFlow']
    instance = flow_class(reset_after=False)
    instance.update_file_path = 'missing-passport.bin'
    instance.back = lambda: events.append(('back', None))
    instance.set_result = lambda result: events.append(('result', result))
    instance.goto = lambda state, save_curr=True: events.append(('goto', state.__name__))

    def show():
        asyncio.run(instance.show_firmware_details())
        return events

    return types.SimpleNamespace(show=show, card=card)


def test_missing_card_offers_insert_then_goes_back(flow):
    assert flow.show() == [('InsertMicroSDPage', None), ('back', None)]


def test_missing_card_retries_once_inserted(flow):
    # Returning without a transition runs this step again.
    flow.card['insert'] = True
    assert flow.show() == [('InsertMicroSDPage', None)]


def test_unreadable_file_reports_an_error(flow):
    flow.card['missing'] = False
    assert flow.show() == [('ErrorPage', 'Could not read firmware file'), ('result', False)]
