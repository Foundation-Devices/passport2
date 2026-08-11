# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression tests for Passport's startup import budget.

The Color device has a small MicroPython heap.  Importing transaction and
wallet-policy implementation modules from the package aggregators can exhaust
that heap before LVGL replaces the bootloader splash screen.
"""

import ast
from pathlib import Path


MODULES = Path(__file__).resolve().parents[2]
MANIFEST = MODULES.parent / 'manifest.py'


def _top_level_imports(relative_path):
    tree = ast.parse((MODULES / relative_path).read_text())
    imports = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            imports.add(node.module or '')
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    return imports


def _nested_imports(relative_path):
    tree = ast.parse((MODULES / relative_path).read_text())
    top_level_ids = {id(node) for node in tree.body}
    imports = set()
    for node in ast.walk(tree):
        if id(node) in top_level_ids:
            continue
        if isinstance(node, ast.ImportFrom):
            imports.add(node.module or '')
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    return imports


def test_heavy_policy_tasks_are_not_imported_during_boot():
    imports = _top_level_imports('tasks/__init__.py')
    assert not {
        'restore_backup_task',
        'search_for_address_task',
        'sign_psbt_task',
        'wallet_policy_task',
    } & imports


def test_wallet_policy_flow_is_not_imported_during_boot():
    assert 'wallet_policy_flow' not in _top_level_imports('flows/__init__.py')


def test_heavy_tasks_are_loaded_only_when_their_flows_need_them():
    assert 'tasks.restore_backup_task' in _nested_imports('flows/restore_backup_flow.py')
    assert 'tasks.sign_psbt_task' in _nested_imports('flows/sign_psbt_common_flow.py')
    assert 'tasks.search_for_address_task' in _nested_imports('flows/verify_address_flow.py')


def test_wallet_policy_ui_is_loaded_only_when_its_menu_is_opened():
    assert 'flows.wallet_policy_flow' not in _top_level_imports('menus.py')
    assert 'flows.wallet_policy_flow' in _nested_imports('menus.py')


def test_lazily_imported_wallet_policy_helpers_are_frozen():
    manifest = MANIFEST.read_text()
    assert "'psbt_display.py'" in manifest
    assert "'tasks/search_for_address_task.py'" in manifest
