import pytest
from fido2.ctap1 import APDU, CTAP1, ApduError
from fido2.utils import sha256

from tests.utils import FidoRequest, verify


class TestU2F(object):
    def test_u2f_reg(self, device, RegRes):
        RegRes.verify(RegRes.request.appid, RegRes.request.challenge)

    def test_u2f_auth(self, device, RegRes, AuthRes):
        AuthRes.verify(
            AuthRes.request.appid, AuthRes.request.challenge, RegRes.public_key
        )

    def test_u2f_auth_check_only(self, device, RegRes):
        with pytest.raises(ApduError) as e:
            device.ctap1.authenticate(
                RegRes.request.challenge,
                RegRes.request.appid,
                RegRes.key_handle,
                check_only=True,
            )
        assert e.value.code == APDU.USE_NOT_SATISFIED

    def test_version(self, device):
        assert device.ctap1.get_version() == "U2F_V2"

    def test_bad_ins(self, device):
        with pytest.raises(ApduError) as e:
            device.ctap1.send_apdu(0, 0, 0, 0, b"")
        assert e.value.code == 0x6D00

    def test_bad_cla(self, device):
        with pytest.raises(ApduError) as e:
            device.ctap1.send_apdu(1, CTAP1.INS.VERSION, 0, 0, b"abc")
        assert e.value.code == 0x6E00

    @pytest.mark.parametrize("iterations", (5,))
    def test_u2f(self, device, iterations):
        lastc = 0
        chal = FidoRequest().challenge
        appid = FidoRequest().appid

        regs = []

        for i in range(0, iterations):
            print("U2F reg + auth %d/%d (count: %02x)" % (i + 1, iterations, lastc))
            reg = device.register(chal, appid)
            reg.verify(appid, chal)
            auth = device.authenticate(chal, appid, reg.key_handle)
            auth.verify(appid, chal, reg.public_key)

            regs.append(reg)
            # check endianness
            if lastc:
                assert (auth.counter - lastc) < 256
            lastc = auth.counter
            if lastc > 0x80000000:
                print("WARNING: counter is unusually high: %04x" % lastc)
                assert 0

        for i in range(0, iterations):
            auth = device.authenticate(chal, appid, regs[i].key_handle)
            auth.verify(appid, chal, regs[i].public_key)

        device.reboot()

        for i in range(0, iterations):
            auth = device.authenticate(chal, appid, regs[i].key_handle)
            auth.verify(appid, chal, regs[i].public_key)

        print("Check that all previous credentials are registered...")
        for i in range(0, iterations):
            with pytest.raises(ApduError) as e:
                auth = device.ctap1.authenticate(
                    chal, appid, regs[i].key_handle, check_only=True
                )
            assert e.value.code == APDU.USE_NOT_SATISFIED

    def test_bad_key_handle(self, device, RegRes):
        kh = bytearray(RegRes.key_handle)
        kh[0] = kh[0] ^ (0x40)

        with pytest.raises(ApduError) as e:
            device.ctap1.authenticate(
                RegRes.request.challenge, RegRes.request.appid, kh, check_only=True
            )
        assert e.value.code == APDU.WRONG_DATA

        with pytest.raises(ApduError) as e:
            device.ctap1.authenticate(
                RegRes.request.challenge, RegRes.request.appid, kh
            )
        assert e.value.code == APDU.WRONG_DATA

    def test_bad_key_handle_length(self, device, RegRes):
        kh = bytearray(RegRes.key_handle)

        with pytest.raises(ApduError) as e:
            device.ctap1.authenticate(
                RegRes.request.challenge, RegRes.request.appid, kh[: len(kh) // 2]
            )
        assert e.value.code == APDU.WRONG_DATA

    def test_incorrect_appid(self, device, RegRes):

        badid = bytearray(RegRes.request.appid)
        badid[0] = badid[0] ^ (0x40)
        with pytest.raises(ApduError) as e:
            auth = device.ctap1.authenticate(
                RegRes.request.challenge, badid, RegRes.key_handle
            )
        assert e.value.code == APDU.WRONG_DATA
