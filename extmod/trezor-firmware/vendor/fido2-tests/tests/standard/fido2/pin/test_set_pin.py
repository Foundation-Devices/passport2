import sys
import pytest
from fido2.ctap import CtapError
from fido2.ctap2 import ES256, AttestedCredentialData, PinProtocolV1

from tests.utils import *


@pytest.mark.skipif('trezor' in sys.argv, reason="ClientPin is not supported on Trezor.")
class TestSetPin(object):
    def test_send_zero_length_pin_auth(self, resetDevice):
        with pytest.raises(CtapError) as e:
            reg = resetDevice.sendMC(*FidoRequest(pin_auth=b"").toMC())
        assert e.value.code == CtapError.ERR.PIN_NOT_SET

        with pytest.raises(CtapError) as e:
            reg = resetDevice.sendGA(*FidoRequest(pin_auth=b"").toGA())
        assert e.value.code in (CtapError.ERR.PIN_NOT_SET, CtapError.ERR.NO_CREDENTIALS)

    def test_set_pin(self, device):
        device.client.pin_protocol.set_pin("TestPin")
        device.reset()

    def test_set_pin_too_big(self, device):
        with pytest.raises(CtapError) as e:
            device.client.pin_protocol.set_pin("A" * 64)
        assert e.value.code == CtapError.ERR.PIN_POLICY_VIOLATION

    def test_get_pin_token_but_no_pin_set(self, device):
        with pytest.raises(CtapError) as e:
            device.client.pin_protocol.get_pin_token("TestPin")
        assert e.value.code == CtapError.ERR.PIN_NOT_SET

    def test_change_pin_but_no_pin_set(self, device):
        with pytest.raises(CtapError) as e:
            device.client.pin_protocol.change_pin("TestPin", "1234")
        assert e.value.code == CtapError.ERR.PIN_NOT_SET

    def test_setting_pin_and_get_info(self, device):
        device.client.pin_protocol.set_pin("TestPin")

        with pytest.raises(CtapError) as e:
            device.client.pin_protocol.set_pin("TestPin")

        info = device.ctap2.get_info()

        assert info.options["clientPin"]

        pin_token = device.client.pin_protocol.get_pin_token("TestPin")

        res = device.sendCP(1, PinProtocolV1.CMD.GET_RETRIES)
        assert res[3] == 8

        device.reset()
