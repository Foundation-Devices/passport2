import sys
import pytest
from fido2.ctap import CtapError
from fido2.ctap2 import ES256, AttestedCredentialData, PinProtocolV1

from tests.utils import *


@pytest.mark.skipif('trezor' in sys.argv, reason="ClientPin is not supported on Trezor.")
def test_lockout(device, resetDevice):
    pin = "TestPin"
    device.client.pin_protocol.set_pin(pin)

    pin_token = device.client.pin_protocol.get_pin_token(pin)
    req = FidoRequest(pin_token=pin_token)

    req.pin_auth = hmac_sha256(pin_token, req.cdh)[:16]

    for i in range(1, 10):
        err = CtapError.ERR.PIN_INVALID
        if i in (3, 6):
            err = CtapError.ERR.PIN_AUTH_BLOCKED
        elif i >= 8:
            err = [CtapError.ERR.PIN_BLOCKED, CtapError.ERR.PIN_INVALID]

        with pytest.raises(CtapError) as e:
            device.sendPP("WrongPin")
        assert e.value.code == err or e.value.code in err

        attempts = 8 - i
        if i > 8:
            attempts = 0

        res = device.ctap2.client_pin(1, PinProtocolV1.CMD.GET_RETRIES)
        assert res[3] == attempts

        if err == CtapError.ERR.PIN_AUTH_BLOCKED:
            device.reboot()

    with pytest.raises(CtapError) as e:
        device.sendMC(*req.toMC())

    device.reboot()

    with pytest.raises(CtapError) as e:
        device.sendPP(pin)
    assert e.value.code == CtapError.ERR.PIN_BLOCKED
