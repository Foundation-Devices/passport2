# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Human-readable, bounded presentation of registered wallet policies.

The strings in this module are derived exclusively from the policy AST that
Passport already validated.  Coordinator-supplied descriptions must never be
used in place of this analysis: a hostile description could otherwise conceal
different spending conditions in the descriptor.
"""

from miniscript import iter_policy_keys, policy_timelocks


_WRAPPERS = ('a', 's', 'c', 'd', 'v', 'j', 'n')
_AND = ('and_v', 'and_b')
_OR = ('or_b', 'or_c', 'or_d', 'or_i')


def _group_number(value):
    text = str(value)
    parts = []
    while len(text) > 3:
        parts.insert(0, text[-3:])
        text = text[:-3]
    parts.insert(0, text)
    return ','.join(parts)


def format_fingerprint(fingerprint):
    text = fingerprint.upper()
    return ' '.join(text[index:index + 4] for index in range(0, len(text), 4))


def _escape(text):
    # LVGL uses # as an inline recolor delimiter. Signer names are local and
    # validated, but still need escaping before they enter a recolor-enabled label.
    return text.replace('#', '##')


def _plural(value, singular, plural=None):
    return '{} {}'.format(value, singular if value == 1 else (plural or singular + 's'))


def _about_duration(seconds):
    # These are intentionally approximate. Block-based locks are not wall-clock
    # guarantees, and time-based BIP68 locks are quantized in 512-second units.
    units = (
        (31557600, 'year'),
        (2629800, 'month'),
        (604800, 'week'),
        (86400, 'day'),
        (3600, 'hour'),
        (60, 'minute'),
    )
    for position, (size, name) in enumerate(units):
        if seconds >= size:
            count = seconds // size
            parts = [_plural(count, name)]
            if position + 1 < len(units):
                next_size, next_name = units[position + 1]
                remainder = seconds - count * size
                next_count = int((remainder + next_size // 2) // next_size)
                if next_count:
                    # Carry a rounded sub-unit into the primary unit. This is
                    # especially important for 11 months 29 days -> 1 year.
                    ratio = int((size + next_size // 2) // next_size)
                    if next_count >= ratio:
                        count += 1
                        parts = [_plural(count, name)]
                    else:
                        parts.append(_plural(next_count, next_name))
            return 'about ' + ' '.join(parts)
    return _plural(seconds, 'second')


def _utc_date(timestamp):
    try:
        try:
            import utime as time
        except ImportError:  # pragma: no cover - CPython host tests
            import time
        value = time.gmtime(timestamp)
        return '{:04d}-{:02d}-{:02d} UTC'.format(value[0], value[1], value[2])
    except BaseException:
        return None


def describe_timelock(kind, value):
    """Return (short description, exact value, explanatory detail)."""
    if kind == 'older':
        if value & (1 << 22):
            units = value & 0xffff
            seconds = units * 512
            exact = '{} seconds ({} x 512)'.format(
                _group_number(seconds), _group_number(units))
            if value != ((1 << 22) | units):
                exact += ' (encoded as older({}))'.format(value)
            return (
                _about_duration(seconds),
                exact,
                'The timer starts separately when each coin confirms.',
            )
        blocks = value & 0xffff
        exact = '{} {}'.format(_group_number(blocks),
                               'block' if blocks == 1 else 'blocks')
        if value != blocks:
            exact += ' (encoded as older({}))'.format(value)
        return (
            _about_duration(blocks * 600),
            exact,
            'The timer starts separately when each coin confirms.',
        )
    if value < 500000000:
        return (
            'block {}'.format(_group_number(value)),
            'absolute block height',
            'This condition uses a blockchain height, not the age of each coin.',
        )
    date = _utc_date(value)
    return (
        date or 'Unix time {}'.format(_group_number(value)),
        'Unix timestamp {}'.format(_group_number(value)),
        'This condition uses an absolute time, not the age of each coin.',
    )


def _unwrap(node):
    while node.kind in _WRAPPERS and len(node.args) == 1:
        node = node.args[0]
    return node


def _split_alternatives(node):
    node = _unwrap(node)
    if node.kind in _OR:
        result = []
        for child in node.args:
            result.extend(_split_alternatives(child))
        return result
    return [node]


def _key_indexes(node):
    result = []
    for key in iter_policy_keys(node):
        if key.index not in result:
            result.append(key.index)
    return tuple(result)


def _can_satisfy_without_key(node, key_index):
    """Whether a positive satisfaction can omit key_index.

    ``None`` means the conditional structure cannot be summarized safely.  The
    UI reports that uncertainty instead of claiming Passport is required.
    """
    node = _unwrap(node)
    kind = node.kind
    if kind in ('pk_k', 'pk_h'):
        return node.value.index != key_index
    if kind in ('older', 'after', '1'):
        return True
    if kind == '0':
        return False
    if kind in ('multi', 'multi_a'):
        available = sum(1 for key in node.args if key.index != key_index)
        return available >= node.value
    if kind in _AND:
        values = [_can_satisfy_without_key(child, key_index) for child in node.args]
        if False in values:
            return False
        if None in values:
            return None
        return True
    if kind in _OR:
        values = [_can_satisfy_without_key(child, key_index) for child in node.args]
        if True in values:
            return True
        if None in values:
            return None
        return False
    if kind == 'thresh':
        values = [_can_satisfy_without_key(child, key_index) for child in node.args]
        possible = sum(1 for value in values if value is True)
        unknown = sum(1 for value in values if value is None)
        if possible >= node.value:
            return True
        if possible + unknown < node.value:
            return False
        return None
    if kind == 'andor':
        # Correctly describing the dissatisfaction branch requires more than a
        # Boolean authorization tree. Keep the display structural and cautious.
        return None
    return None


def _simple_requirements(node):
    """Flatten a path made only from AND, keys, and timelocks."""
    node = _unwrap(node)
    if node.kind in _AND:
        result = []
        for child in node.args:
            flattened = _simple_requirements(child)
            if flattened is None:
                return None
            result.extend(flattened)
        return result
    if node.kind in ('pk_k', 'pk_h', 'older', 'after'):
        return [node]
    return None


def _key_line(policy, key_index, recovery=False):
    return '{} - {}'.format(
        _key_role(policy, key_index, recovery),
        format_fingerprint(policy.keys[key_index].fingerprint))


def _key_role(policy, key_index, recovery=False):
    if key_index in policy.owned_key_indexes:
        role = 'This Passport'
    elif policy.key_names[key_index]:
        role = _escape(policy.key_names[key_index])
    elif recovery:
        role = 'Recovery key'
    else:
        role = 'Key {}'.format(key_index + 1)
    return role


def _format_condition(node, policy, depth=0, recovery=False):
    node = _unwrap(node)
    indent = '  ' * min(depth, 4)
    child_indent = '  ' * min(depth + 1, 4)
    kind = node.kind

    if kind in ('pk_k', 'pk_h'):
        return [indent + _key_line(policy, node.value.index, recovery)]
    if kind in ('older', 'after'):
        short, exact, _ = describe_timelock(kind, node.value)
        prefix = 'Wait ' if kind == 'older' else 'After '
        return [indent + prefix + short, child_indent + '(' + exact + ')']
    if kind in ('multi', 'multi_a'):
        lines = [indent + '{} of {} keys'.format(node.value, len(node.args))]
        for key in node.args:
            lines.append(child_indent + '- ' + _key_line(policy, key.index, recovery))
        return lines
    if kind in _AND:
        lines = [indent + 'All of']
        for child in node.args:
            child_lines = _format_condition(child, policy, depth + 1, recovery)
            if child_lines:
                child_lines[0] = child_indent + '- ' + child_lines[0].lstrip()
            lines.extend(child_lines)
        return lines
    if kind in _OR:
        lines = [indent + 'Any one of']
        for child in node.args:
            child_lines = _format_condition(child, policy, depth + 1, recovery)
            if child_lines:
                child_lines[0] = child_indent + '- ' + child_lines[0].lstrip()
            lines.extend(child_lines)
        return lines
    if kind == 'thresh':
        lines = [indent + '{} of {} conditions'.format(node.value, len(node.args))]
        for child in node.args:
            child_lines = _format_condition(child, policy, depth + 1, recovery)
            if child_lines:
                child_lines[0] = child_indent + '- ' + child_lines[0].lstrip()
            lines.extend(child_lines)
        return lines
    if kind == 'andor':
        lines = [indent + 'Conditional path', child_indent + 'If']
        lines.extend(_format_condition(node.args[0], policy, depth + 2, recovery))
        lines.append(child_indent + 'Then also')
        lines.extend(_format_condition(node.args[1], policy, depth + 2, recovery))
        lines.append(child_indent + 'Otherwise')
        lines.extend(_format_condition(node.args[2], policy, depth + 2, recovery))
        return lines
    if kind == '1':
        return [indent + 'No additional condition']
    if kind == '0':
        return [indent + 'Unavailable branch']
    # This should be unreachable for the currently accepted profile. Keeping a
    # precise fragment name is safer than silently omitting a future fragment.
    return [indent + 'Advanced condition: ' + kind]


def _make_path(node, leaf_index=None):
    return {
        'node': node,
        'leaf_index': leaf_index,
        'keys': _key_indexes(node),
        'locks': tuple(policy_timelocks(node)),
        'key_path': False,
        'fixed_key_path': False,
    }


def policy_paths(policy):
    paths = []
    if policy.context == 'tr':
        if isinstance(policy.internal_key, bytes):
            paths.append({
                'node': None,
                'leaf_index': None,
                'keys': (),
                'locks': (),
                'key_path': True,
                'fixed_key_path': True,
            })
        else:
            paths.append({
                'node': None,
                'leaf_index': None,
                'keys': (policy.internal_key.index,),
                'locks': (),
                'key_path': True,
                'fixed_key_path': False,
            })
    for leaf_index, leaf in enumerate(policy._leaves()):
        for alternative in _split_alternatives(leaf):
            paths.append(_make_path(alternative, leaf_index if policy.context == 'tr' else None))
    # Descriptors preserve script order, not human priority. Coordinators such
    # as Liana may serialize a delayed recovery branch before the immediately
    # available branch. Keep each group stable, but review paths that can be
    # used now before paths gated by a timelock.
    return tuple(sorted(paths, key=lambda path: 1 if path['locks'] else 0))


def _classify_simple_inheritance(policy, paths):
    # Taproot always has a key path in addition to its script tree. Keep those
    # policies in the generic renderer so the bypass path cannot be visually
    # reduced to a footnote, even when the script leaves resemble inheritance.
    if any(path['key_path'] for path in paths):
        return None
    script_paths = [path for path in paths if not path['key_path']]
    if len(script_paths) != 2:
        return None
    owned = policy.owned_key_indexes[0]
    primary = None
    recovery = None
    for path in script_paths:
        requirements = _simple_requirements(path['node'])
        if requirements is None:
            return None
        keys = [item.value.index for item in requirements
                if item.kind in ('pk_k', 'pk_h')]
        locks = [(item.kind, item.value) for item in requirements
                 if item.kind in ('older', 'after')]
        if keys == [owned] and not locks:
            primary = path
        elif len(keys) == 1 and keys[0] != owned and len(locks) == 1 and locks[0][0] == 'older':
            recovery = path
    if primary is None or recovery is None:
        return None
    return primary, recovery


def _script_type(policy):
    return 'Native SegWit (P2WSH)' if policy.context == 'wsh' else 'Taproot (P2TR)'


def _network_name(policy):
    return 'Bitcoin' if policy.network == 'BTC' else 'Bitcoin Testnet'


def _path_requires_passport(policy, path):
    if path['key_path']:
        if path['fixed_key_path']:
            return False
        return path['keys'][0] in policy.owned_key_indexes
    result = _can_satisfy_without_key(path['node'], policy.owned_key_indexes[0])
    if result is None:
        return None
    return not result


def _simple_path_pages(policy, simple):
    primary, recovery = simple
    owned = policy.keys[policy.owned_key_indexes[0]]
    recovery_index = recovery['keys'][0]
    recovery_key = policy.keys[recovery_index]
    lock_kind, lock_value = recovery['locks'][0]
    short, exact, detail = describe_timelock(lock_kind, lock_value)
    recovery_name = _escape(policy.key_names[recovery_index]) or 'Recovery key'
    primary_page = (
        'Spend with Passport\n\n'
        'Passport can authorize spending by itself.\n'
        'No recovery delay is required.\n\n'
        'Passport key\n{}\n\n'
        'This key matches the seed currently loaded on Passport.'
    ).format(format_fingerprint(owned.fingerprint))
    recovery_page = (
        'Spend with the recovery key\n\n'
        '{} can spend by itself {} after each coin confirms.\n\n'
        'Exact delay\n{}\n\n'
        'Passport can still spend by itself after the recovery key becomes available.\n\n'
        'Recovery key\n{}'
    ).format(recovery_name, short, exact, format_fingerprint(recovery_key.fingerprint))
    timing_page = (
        'How the recovery delay works\n\n'
        '{}\n\n'
        'Block timing varies. Spending and returning change creates a new coin and restarts its timer.'
    ).format(detail)
    return (primary_page, recovery_page, timing_page)


def suggested_key_name(policy, key_index):
    paths = policy_paths(policy)
    simple = _classify_simple_inheritance(policy, paths)
    if simple and key_index == simple[1]['keys'][0]:
        return 'Recovery key'
    return 'Key {}'.format(key_index + 1)


def _flatten_conjunction(node):
    """Return top-level AND requirements without changing their meaning."""
    node = _unwrap(node)
    if node.kind not in _AND:
        return [node]
    result = []
    for child in node.args:
        result.extend(_flatten_conjunction(child))
    return result


def _key_threshold(node):
    """Return (required, key indexes) for a keys-only threshold."""
    node = _unwrap(node)
    if node.kind in ('pk_k', 'pk_h'):
        return 1, (node.value.index,)
    if node.kind in ('multi', 'multi_a'):
        return node.value, tuple(key.index for key in node.args)
    if node.kind == 'thresh':
        indexes = []
        for child in node.args:
            child = _unwrap(child)
            if child.kind not in ('pk_k', 'pk_h'):
                return None
            indexes.append(child.value.index)
        return node.value, tuple(indexes)
    return None


def _path_key_threshold(path):
    """Return a simple threshold for the path, when it has one."""
    requirements = _flatten_conjunction(path['node'])
    key_groups = []
    for requirement in requirements:
        requirement = _unwrap(requirement)
        if requirement.kind in ('older', 'after'):
            continue
        threshold = _key_threshold(requirement)
        if threshold is None:
            return None
        key_groups.append(threshold)

    if not key_groups:
        return None

    # Separate ANDed key checks are equivalent to requiring every listed key.
    if len(key_groups) > 1:
        if any(required != 1 or len(indexes) != 1
               for required, indexes in key_groups):
            return None
        indexes = tuple(indexes[0] for _, indexes in key_groups)
        required = len(indexes)
    else:
        required, indexes = key_groups[0]

    return required, indexes


def _friendly_key_path(policy, path):
    """Summarize common key thresholds without parser-shaped indentation."""
    threshold = _path_key_threshold(path)
    if threshold is None:
        return None
    required, indexes = threshold

    if required == len(indexes) == 2:
        summary = 'Both keys must sign'
    elif required == len(indexes):
        summary = 'All {} keys must sign'.format(len(indexes))
    elif required == 1:
        summary = 'Any 1 of {} keys must sign'.format(len(indexes))
    else:
        summary = 'Any {} of {} keys must sign'.format(required, len(indexes))

    lines = [summary]
    for key_index in indexes:
        lines.extend([
            '',
            _key_role(policy, key_index),
            format_fingerprint(policy.keys[key_index].fingerprint),
        ])
    return lines


def _path_name(path):
    if path['key_path']:
        name = 'Taproot key path'
    elif len(path['locks']) == 1:
        name = 'After {}'.format(describe_timelock(*path['locks'][0])[0])
    elif path['locks']:
        name = 'Delayed spending'
    else:
        name = 'Spend now'

    if not path['key_path']:
        threshold = _path_key_threshold(path)
        if threshold is not None:
            required, indexes = threshold
            name += ' ({}-of-{})'.format(required, len(indexes))
    return name


def compatible_path_indexes(policy, tx_version, lock_time, sequence):
    """Return paths whose timelocks are permitted by the transaction fields.

    This does not claim that a timelock has matured. It only rules out paths
    that the signed transaction itself cannot satisfy. Paths without locks
    always remain possible until the final witness selects a branch.
    """
    compatible = []
    for index, path in enumerate(policy_paths(policy)):
        allowed = True
        for kind, value in path['locks']:
            if kind == 'older':
                # BIP68/112: version 2, disable flag clear, matching time or
                # height units, and a sequence value at least as large.
                if tx_version < 2 or sequence & (1 << 31):
                    allowed = False
                    break
                type_flag = 1 << 22
                if sequence & type_flag != value & type_flag or \
                        sequence & 0xffff < value & 0xffff:
                    allowed = False
                    break
            elif kind == 'after':
                # BIP65: a final sequence disables locktime, and height/time
                # lock types cannot be mixed.
                if sequence == 0xffffffff or \
                        (lock_time < 500000000) != (value < 500000000) or \
                        lock_time < value:
                    allowed = False
                    break
        if allowed:
            compatible.append(index)
    return tuple(compatible)


def _generic_path_page(policy, path):
    requires = _path_requires_passport(policy, path)
    if path['key_path']:
        if path['fixed_key_path']:
            return (
                'Taproot key path\n\n'
                'A fixed internal key can bypass every script condition if its private key exists.\n\n'
                'Passport cannot verify that no one controls this key.'
            )
        key_index = path['keys'][0]
        return (
            'Taproot key path\n\n'
            '{} can spend without using any script-path conditions.\n\n'
            'This path {} Passport.'
        ).format(_key_line(policy, key_index),
                 'requires' if requires else 'does not require')

    locks = path['locks']
    if locks:
        heading = 'Delayed spending'
    else:
        heading = 'Spend now'
    lines = [heading, '']

    if locks:
        for lock_position, (kind, value) in enumerate(locks):
            short, exact, _ = describe_timelock(kind, value)
            if lock_position:
                lines.append('')
            lines.extend([
                'Available after {}'.format(short),
                '{}: {}'.format(
                    'Exact delay' if kind == 'older' else 'Exact condition',
                    exact),
            ])
    friendly = _friendly_key_path(policy, path)
    if locks:
        lines.append('')
    if friendly is None:
        lines.extend(_format_condition(path['node'], policy))
    else:
        lines.extend(friendly)
    if requires is False:
        lines.append('')
        if any(key_index in policy.owned_key_indexes for key_index in path['keys']):
            lines.append('This Passport is optional.')
        else:
            lines.append('This Passport is not used.')
    elif requires is True and friendly is None:
        lines.extend(['', 'This Passport must sign.'])
    else:
        if friendly is None:
            lines.extend(['', 'Review the conditional branches carefully.'])
    return '\n'.join(lines)


def format_review_pages(policy):
    paths = policy_paths(policy)
    simple = _classify_simple_inheritance(policy, paths)
    kind = 'Simple inheritance' if simple else 'Custom wallet policy'
    overview = (
        '{}\n\n{}\n\n{}\n{}\n\n{}'
    ).format(_escape(policy.name), kind, _network_name(policy), _script_type(policy),
             _plural(len(paths), 'way to spend', 'ways to spend'))

    pages = [overview]
    if simple:
        pages.extend(_simple_path_pages(policy, simple))
    else:
        for path in paths:
            pages.append(_generic_path_page(policy, path))

    if not simple and len(paths) > 1:
        lines = ['This Passport']
        for path in paths:
            requires = _path_requires_passport(policy, path)
            if requires is True:
                role = 'must sign'
            elif requires is False:
                if any(key_index in policy.owned_key_indexes
                       for key_index in path['keys']):
                    role = 'optional'
                else:
                    role = 'not used'
            else:
                role = 'review details'
            lines.extend(['', _path_name(path), role.capitalize()])
        pages.append('\n'.join(lines))

    pages.append(
        'Back up this policy\n\n'
        'Your seed recovers this Passport key, not the policy.\n\n'
        'Keep a separate copy.'
    )
    return tuple(pages)


def format_confirmation(policy):
    paths = policy_paths(policy)
    simple = _classify_simple_inheritance(policy, paths)
    if simple:
        _, recovery = simple
        key = policy.keys[recovery['keys'][0]]
        short, _, _ = describe_timelock(*recovery['locks'][0])
        return (
            'Passport can spend by itself with no recovery delay.\n\n'
            '{} {}\ncan spend by itself {} after each coin confirms.'
        ).format(_escape(policy.key_names[recovery['keys'][0]]) or 'Recovery',
                 format_fingerprint(key.fingerprint), short)
    bypass = sum(1 for path in paths if _path_requires_passport(policy, path) is False)
    text = _plural(len(paths), 'spending path')
    if bypass:
        text += '\n{} without Passport'.format(bypass)
    return text


def format_signing_pages(policy, compatible_indexes=None):
    all_paths = policy_paths(policy)
    paths = all_paths
    if compatible_indexes is not None:
        filtered = tuple(all_paths[index] for index in compatible_indexes
                         if 0 <= index < len(all_paths))
        if filtered:
            paths = filtered
    simple = _classify_simple_inheritance(policy, paths)
    owned = policy.keys[policy.owned_key_indexes[0]]
    if simple:
        return ((
            'Signing path\n\n'
            'Wallet\n{}\n\n'
            'Passport is authorizing this transaction with its own key.\n'
            'No recovery delay is required.\n\n'
            'Passport key\n{}\n\n'
            'The recovery key is not being used.'
        ).format(_escape(policy.name), format_fingerprint(owned.fingerprint)),)

    if len(paths) == 1 and policy.owned_key_indexes[0] in paths[0]['keys']:
        friendly = _friendly_key_path(policy, paths[0])
        if friendly is not None:
            return (('\n'.join([
                'Wallet',
                _escape(policy.name),
                '',
                _path_name(paths[0]),
                '',
            ] + friendly)),)

    roles = []
    for path in paths:
        if policy.owned_key_indexes[0] in path['keys']:
            requires = _path_requires_passport(policy, path)
            if requires is True:
                role = 'required'
            elif requires is False:
                role = 'optional'
            else:
                role = 'may be required'
            roles.append('{}: {}'.format(_path_name(path), role))
    return ((
        'Wallet\n{}\n\n'
        'This Passport will sign:\n{}\n\n'
        'Key: {}\n\n'
        'Your wallet app chooses which valid option completes the transaction.'
    ).format(_escape(policy.name), '\n'.join(roles),
             format_fingerprint(owned.fingerprint)),)
