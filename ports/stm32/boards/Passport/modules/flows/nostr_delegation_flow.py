# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_delegation_flow.py - Sign a nostr delegation token

from flows import Flow


def created_at_helper(carrot, created_at):
    from utils import timestamp_to_str
    created = [c for c in created_at if c.count(carrot)]
    assert len(created) <= 1, 'There must only be 1 "created {}" condition.'.format(
        'before' if carrot == '<' else 'after')

    if len(created) == 0:
        return None

    created = int(created[0].split(carrot)[1])
    return timestamp_to_str(created)


event_kind = {
    0: 'Metadata',
    1: 'Short Text Notes',
    2: 'Recommend Relays',
    3: 'Contacts',
    4: 'Encrypted Direct Messages',
    5: 'Event Deletion',
    6: 'Reposts',
    7: 'Reactions',
    8: 'Badge Awards',
    40: 'Channel Creation',
    41: 'Channel Metadata',
    42: 'Channel Messages',
    43: 'Channel Hide Messages',
    44: 'Channel Mute Users',
    1984: 'Reporting',
    9731: 'Zap Requests',
    9735: 'Zaps',
    10000: 'Mute Lists',
    10001: 'Pin Lists',
    10002: 'Relay List Metadata',
    24133: 'Nostr Connect',
    30000: 'Categorized People Lists',
    30001: 'Categorized Bookmark Lists',
    30008: 'Profile Badges',
    30009: 'Badge Definitions',
    30023: 'Long-Form Content',
    30078: 'Application-Specific Data',
}


def parse_delegation_string(delegation_string):
    from ubinascii import unhexlify as a2b_hex
    from utils import nostr_nip19_from_key, recolor
    import uio
    import re
    from styles.colors import HIGHLIGHT_TEXT_HEX

    fields = delegation_string.split(':')
    num_fields = len(fields)
    assert num_fields == 4, \
        'Invalid delegation string: must have 4 fields, found {}'.format(num_fields)
    assert fields[0] == 'nostr' and fields[1] == 'delegation', \
        'First 2 fields of delegation string must be "nostr:delegation:"'

    # exceptions handled by caller
    # TODO: make these exceptions prettier
    delegatee = a2b_hex(fields[2])

    # TODO: check length before converting to npub

    delegatee_npub = nostr_nip19_from_key(delegatee, "npub")

    conditions = fields[3].split('&')
    num_conditions = len(conditions)
    assert num_conditions > 0, \
        'Delegation conditions are required, found {}'.format(num_conditions)

    assert len(set(conditions)) == len(conditions), "Duplicate conditions found"

    # TODO: what are the condition parsing rules? Can multiple kinds be given different
    # created_at rules within 1 delegation? I assume not for now. This means
    # all 'kind' conditions must come before all 'created_at' conditions.

    kind_pattern = re.compile('^kind=\\d+$')
    created_at_pattern = re.compile('^created_at[\\<\\>]\\d+$')
    kinds = []
    created_at = []

    # Get all kinds
    for c in conditions:
        if kind_pattern.search(c):
            kinds.append(c)
        else:
            break

    # remove all found kinds from conditions before continuing
    conditions = list(set(conditions) - set(kinds))

    # Get all created_at
    for c in conditions:
        if created_at_pattern.search(c):
            created_at.append(c)
        else:
            assert not kind_pattern.search(c), \
                'All "kinds" must come before all "created_at" conditions.'
            break

    assert len(created_at) <= 2, 'There must be at most 2 "created_at" conditions.'

    created_before = created_at_helper('<', created_at)
    created_after = created_at_helper('>', created_at)

    # len(kinds) + len(created_at) == len(conditions) iff all conditions are valid and
    # all 'kinds' come before all 'created_at', but we already removed 'kinds'
    assert len(created_at) == len(conditions), 'Invalid conditions found'

    kinds = list(map(lambda k: int(k.split('=')[1]), kinds))

    # All inputs checked, format description and warnings

    details = uio.StringIO()
    details.write("\n{}\n{}".format(
        recolor(HIGHLIGHT_TEXT_HEX, 'Delegating To:'),
        delegatee_npub))

    details.write("\n\n")

    if created_after is not None:
        details.write("{}\n{}\n{}".format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Delegation Start Date:'),
            created_after,
            "Make sure this time isn't in the past!"))
    else:
        details.write("{}\n{}".format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Warning:'),
            "No start date, use caution!"))

    details.write("\n\n")

    if created_before is not None:
        details.write("{}\n{}".format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Delegation End Date:'),
            created_before))
    else:
        details.write("{}\n{}".format(
            recolor(HIGHLIGHT_TEXT_HEX, 'Warning:'),
            "No end date, use caution!"))

    details.write("\n\n")

    details.write("{}".format(
        recolor(HIGHLIGHT_TEXT_HEX, 'Event Types:')))

    for k in kinds:
        details.write("\n{}: {}".format(
            k, event_kind.get(k, "Unknown event, use caution!")))

    return details.getvalue()


class NostrDelegationFlow(Flow):
    def __init__(self, context=None):
        from derived_key import get_key_type_from_tn

        self.key = context
        self.key_type = get_key_type_from_tn(self.key['tn'])
        self.pk = None
        self.npub = None
        self.delegation_string = None
        super().__init__(initial_state=self.export_npub, name='NostrDelegationFlow')

    async def export_npub(self):
        from utils import spinner_task
        from pages import ShowQRPage, ErrorPage
        from ubinascii import unhexlify as a2b_hex

        (vals, error) = await spinner_task(text='Generating npub',
                                                task=self.key_type['task'],
                                                args=[self.key['index']])
        self.pk = vals['pk']
        # self.pk = a2b_hex("ee35e8bb71131c02c1d7e73231daa48e9953d329a4b701f7133c8f46dd21139c")
        self.npub = vals['npub']

        if not self.pk or not self.npub:
            await ErrorPage("Failed to generate npub and nsec").show()
            self.set_result(False)
            return

        await ShowQRPage(qr_data=self.npub).show()
        self.goto(self.scan_delegation_string)

    async def scan_delegation_string(self):
        from pages import ScanQRPage, ErrorPage

        # TODO: replace with ScanQRFlow
        result = await ScanQRPage().show()

        if not result:
            self.set_result(False)
            return

        if result.is_failure():
            await ErrorPage('Unable to scan QR code.').show()
            self.set_result(False)
            return

        self.delegation_string = result.data
        self.goto(self.display_details)

    async def display_details(self):
        from pages import ErrorPage, InfoPage, LongTextPage
        from common import settings
        from flows import ChooseTimezoneFlow
        import microns

        if settings.get('timezone', None) is None:
            result = await InfoPage('Nostr delegation is time-sensitive. Please enter your timezone.',
                                    left_micron=microns.Back,
                                    right_micron=microns.Forward).show()
            if not result:
                self.back()
                return
            await ChooseTimezoneFlow().run()

        try:
            details = parse_delegation_string(self.delegation_string)
        except Exception as e:
            await ErrorPage('{}'.format(e)).show()
            self.set_result(False)
            return

        result = await LongTextPage(text=details,
                                    centered=True,
                                    card_header={'title': 'Delegation Details'}).show()
        if not result:
            self.set_result(False)
            return

        self.goto(self.sign_delegation)
        return

    async def sign_delegation(self):
        from serializations import sha256
        from utils import nostr_sign, B2A
        from pages import ShowQRPage

        print("pk: {}".format(B2A(self.pk)))
        sha = sha256(self.delegation_string)
        print("sha: {}".format(B2A(sha)))
        sig = nostr_sign(self.pk, sha)
        print("sig: {}".format(B2A(sig)))

        await ShowQRPage(qr_data=B2A(sig)).show()
        self.set_result(True)
