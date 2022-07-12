import sys
import pytest
from fido2.ctap import CtapError

from tests.utils import *


@pytest.fixture(scope="module", params=["", "123456"])
def SetPINRes(request, device, info):

    device.reset()

    pin = request.param
    req = FidoRequest()

    if pin:
        if "clientPin" in info.options:
            device.client.pin_protocol.set_pin(pin)
            pin_token = device.client.pin_protocol.get_pin_token(pin)
            pin_auth = hmac_sha256(pin_token, req.cdh)[:16]

            req = FidoRequest(req, pin_protocol=1, pin_auth=pin_auth)
        else:
            pytest.skip("PIN not supported")

    res = device.sendMC(*req.toMC())
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="module")
def MC_RK_Res(device, SetPINRes):
    req = FidoRequest(SetPINRes, options={"rk": True})
    res = device.sendMC(*req.toMC())
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="class")
def GA_RK_Res(device, MC_RK_Res):
    req = FidoRequest(MC_RK_Res, options=None)
    res = device.sendGA(*req.toGA())
    setattr(res, "request", req)
    return res


class TestResidentKey(object):
    pytestmark = pytest.mark.random_order(disabled=True)

    def test_resident_key(self, MC_RK_Res, info):
        pass

    def test_resident_key_auth(self, MC_RK_Res, GA_RK_Res):
        verify(MC_RK_Res, GA_RK_Res)

    def test_user_info_returned(self, MC_RK_Res, GA_RK_Res):
        assert "id" in GA_RK_Res.user.keys()
        assert MC_RK_Res.auth_data.credential_data.credential_id == GA_RK_Res.credential['id']
        assert MC_RK_Res.request.user['id'] == GA_RK_Res.user['id']
        if not MC_RK_Res.request.pin_protocol or not GA_RK_Res.number_of_credentials:
            assert "id" in GA_RK_Res.user.keys() and len(GA_RK_Res.user.keys()) == 1
        else:
            assert MC_RK_Res.request.user == GA_RK_Res.user

    @pytest.mark.skipif('trezor' in sys.argv, reason="Trezor does not support get_next_assertion() because it has a display.")
    def test_multiple_rk_nodisplay(self, device, MC_RK_Res):
        auths = []
        regs = [MC_RK_Res]
        for i in range(0, 3):
            req = FidoRequest(MC_RK_Res, user=generate_user())
            res = device.sendMC(*req.toMC())
            regs.append(res)

        req = FidoRequest(MC_RK_Res, options=None, user=generate_user())
        res = device.sendGA(*req.toGA())

        assert res.number_of_credentials == 4

        auths.append(res)
        auths.append(device.ctap2.get_next_assertion())
        auths.append(device.ctap2.get_next_assertion())
        auths.append(device.ctap2.get_next_assertion())

        with pytest.raises(CtapError) as e:
            device.ctap2.get_next_assertion()

        assert len(regs) == 4
        assert len(regs) == len(auths)

        if MC_RK_Res.request.pin_protocol:
            for x in auths:
                for y in ("name", "icon", "displayName", "id"):
                    if y not in x.user.keys():
                        print("FAIL: %s was not in user: " % y, x.user)

        for x, y in zip(regs, auths[::-1]):
            verify(x, y, req.cdh)

    @pytest.mark.skipif('trezor' not in sys.argv, reason="Only Trezor has a display.")
    def test_multiple_rk_display(self, device, MC_RK_Res):
        regs = [MC_RK_Res]
        for i in range(0, 3):
            req = FidoRequest(MC_RK_Res, user=generate_user())
            res = device.sendMC(*req.toMC())
            setattr(res, "request", req)
            regs.append(res)

        for i, reg in enumerate(reversed(regs)):
            req = FidoRequest(MC_RK_Res, options=None, on_keepalive=DeviceSelectCredential(i + 1))
            res = device.sendGA(*req.toGA())
            assert res.number_of_credentials is None

            with pytest.raises(CtapError) as e:
                device.ctap2.get_next_assertion()
            assert e.value.code == CtapError.ERR.NOT_ALLOWED

            assert res.user["id"] == reg.request.user["id"]
            verify(reg, res, req.cdh)

    @pytest.mark.skipif('trezor' not in sys.argv, reason="Only Trezor has a display.")
    def test_replace_rk_display(self, device):
        """
        Test replacing resident keys.
        """
        user1 = generate_user()
        user2 = generate_user()
        rp1 = {"id": "example.org", "name": "Example"}
        rp2 = {"id": "example.com", "name": "Example"}

        # Registration data is a list of (rp, user, number), where number is
        # the expected position of the credential after all registrations are
        # complete.
        reg_data = [(rp1, user1, 2), (rp1, user2, None), (rp1, user2, 1), (rp2, user2, 1)]
        regs = []
        for rp, user, number in reg_data:
            req = FidoRequest(options={"rk": True}, rp=rp, user=user)
            res = device.sendMC(*req.toMC())
            setattr(res, "request", req)
            setattr(res, "number", number)
            regs.append(res)

        # Check.
        for reg in regs:
            if reg.number is not None:
                req = FidoRequest(rp=reg.request.rp, options=None, on_keepalive=DeviceSelectCredential(reg.number))
                res = device.sendGA(*req.toGA())
                assert res.user["id"] == reg.request.user["id"]
                verify(reg, res, req.cdh)

    @pytest.mark.skipif('trezor' in sys.argv, reason="Trezor does not support get_next_assertion() because it has a display.")
    @pytest.mark.skipif('solokeys' in sys.argv, reason="Initial SoloKeys model truncates displayName")
    def test_rk_maximum_size_nodisplay(self, device, MC_RK_Res):
        """
        Check the lengths of the fields according to the FIDO2 spec
        https://github.com/solokeys/solo/issues/158#issue-426613303
        https://www.w3.org/TR/webauthn/#dom-publickeycredentialuserentity-displayname
        """
        auths = []
        user_max = generate_user_maximum()
        req = FidoRequest(MC_RK_Res, user=user_max)
        resMC = device.sendMC(*req.toMC())
        req.options={}
        resGA = device.sendGA(*req.toGA())
        credentials = resGA.number_of_credentials
        assert credentials == 5

        auths.append(resGA)
        for i in range(credentials - 1):
            auths.append(device.ctap2.get_next_assertion())

        user_max_GA = auths[0]
        verify(resMC, user_max_GA, req.cdh)

        if MC_RK_Res.request.pin_protocol:
            for y in ("name", "icon", "displayName", "id"):
                assert user_max_GA.user[y] == user_max[y]

    @pytest.mark.skipif('trezor' not in sys.argv, reason="Only Trezor has a display.")
    def test_rk_maximum_size_display(self, device, MC_RK_Res):
        """
        Check the lengths of the fields according to the FIDO2 spec
        https://github.com/solokeys/solo/issues/158#issue-426613303
        https://www.w3.org/TR/webauthn/#dom-publickeycredentialuserentity-displayname
        """
        user_max = generate_user_maximum()
        req = FidoRequest(MC_RK_Res, user=user_max)
        resMC = device.sendMC(*req.toMC())
        req = FidoRequest(MC_RK_Res, options=None)
        resGA = device.sendGA(*req.toGA())
        assert resGA.number_of_credentials is None
        verify(resMC, resGA, req.cdh)

    @pytest.mark.skipif('trezor' in sys.argv, reason="Trezor does not support get_next_assertion() because it has a display.")
    @pytest.mark.skipif('solokeys' in sys.argv, reason="Initial SoloKeys model truncates displayName")
    def test_rk_maximum_list_capacity_per_rp_nodisplay(self, device, MC_RK_Res):
        """
        Test maximum returned capacity of the RK for the given RP
        """
        RK_CAPACITY_PER_RP = 19
        users = []

        def get_user():
            user = generate_user_maximum()
            users.append(user)
            return user

        req = FidoRequest(MC_RK_Res, options=None, user=get_user())
        res = device.sendGA(*req.toGA())
        current_credentials_count = res.number_of_credentials

        auths = []
        regs = [MC_RK_Res]
        RK_to_generate = RK_CAPACITY_PER_RP - current_credentials_count
        for i in range(RK_to_generate):
            req = FidoRequest(MC_RK_Res, user=get_user())
            res = device.sendMC(*req.toMC())
            regs.append(res)

        req = FidoRequest(MC_RK_Res, options=None, user=generate_user_maximum())
        res = device.sendGA(*req.toGA())
        assert res.number_of_credentials == RK_CAPACITY_PER_RP

        auths.append(res)
        for i in range(RK_CAPACITY_PER_RP - 1):
            auths.append(device.ctap2.get_next_assertion())

        with pytest.raises(CtapError) as e:
            device.ctap2.get_next_assertion()

        auths = auths[::-1][-RK_to_generate:]
        regs = regs[-RK_to_generate:]
        users = users[-RK_to_generate:]

        assert len(auths) == len(users)

        if MC_RK_Res.request.pin_protocol:
            for x, u in zip(auths, users):
                for y in ("name", "icon", "displayName", "id"):
                    assert y in x.user.keys()
                    assert x.user[y] == u[y]

        assert len(auths) == len(regs)
        for x, y in zip(regs, auths):
            verify(x, y, req.cdh)

    @pytest.mark.skipif('trezor' not in sys.argv, reason="Only Trezor has a display.")
    def test_rk_maximum_list_capacity_per_rp_display(self, device):
        """
        Test maximum capacity of resident keys.
        """
        RK_CAPACITY = 100
        device.reset()
        req = FidoRequest(options={"rk": True})

        regs = []
        for i in range(RK_CAPACITY):
            req = FidoRequest(req, user=generate_user_maximum())
            res = device.sendMC(*req.toMC())
            setattr(res, "request", req)
            regs.append(res)

        req = FidoRequest(req, user=generate_user_maximum())
        with pytest.raises(CtapError) as e:
            res = device.sendMC(*req.toMC())
        assert e.value.code == CtapError.ERR.KEY_STORE_FULL

        for i, reg in enumerate(reversed(regs)):
            if i not in (0, 1, RK_CAPACITY/2, RK_CAPACITY - 2, RK_CAPACITY - 1):
                continue
            req = FidoRequest(req, options=None, on_keepalive=DeviceSelectCredential(i + 1))
            res = device.sendGA(*req.toGA())
            assert res.user["id"] == reg.request.user["id"]
            verify(reg, res, req.cdh)
