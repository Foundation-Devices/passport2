from fido2.ctap import CtapError

import tests


def test_reset(device):
    device.reset()
