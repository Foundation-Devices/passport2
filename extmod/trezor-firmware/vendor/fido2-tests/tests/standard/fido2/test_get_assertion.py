import sys
import pytest
from fido2.ctap import CtapError
from fido2.utils import hmac_sha256, sha256

from tests.utils import *


class TestGetAssertion(object):
    def test_get_assertion(self, device, MCRes, GARes):
        verify(MCRes, GARes)

    def test_assertion_auth_data(self, GARes):
        assert len(GARes.auth_data) == 37
        assert sha256(GARes.request.rp["id"].encode()) == GARes.auth_data.rp_id_hash

    def test_Check_that_AT_flag_is_not_set(self, GARes):
        assert (GARes.auth_data.flags & 0xF8) == 0

    def test_that_user_credential_and_numberOfCredentials_are_not_present(self, GARes):
        assert GARes.user == None
        assert GARes.number_of_credentials == None

    def test_empty_allowList(self, device):
        device.reset()
        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(allow_list=[]).toGA())
        assert e.value.code == CtapError.ERR.NO_CREDENTIALS

    def test_corrupt_credId(self, device, MCRes):
        # apply bit flip
        badid = list(MCRes.auth_data.credential_data.credential_id[:])
        badid[len(badid) // 2] = badid[len(badid) // 2] ^ 1
        badid = bytes(badid)

        allow_list = [{"id": badid, "type": "public-key"}]

        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(allow_list=allow_list).toGA())
        assert e.value.code == CtapError.ERR.NO_CREDENTIALS

    def test_mismatched_rp(self, device, GARes):
        rp_id = GARes.request.rp['id'][:]
        rp_name = GARes.request.rp['name'][:]
        rp_id += '.com'

        mismatch_rp = {'id': rp_id, 'name': rp_name}

        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, rp=mismatch_rp).toGA())
        assert e.value.code == CtapError.ERR.NO_CREDENTIALS


    def test_missing_rp(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, rp=None).toGA())
        assert e.value.code == CtapError.ERR.MISSING_PARAMETER

    def test_bad_rp(self, device, GARes):

        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, rp={"id": {"type": "wrong"}}).toGA())

    def test_missing_cdh(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, cdh=None).toGA())
        assert e.value.code == CtapError.ERR.MISSING_PARAMETER

    def test_bad_cdh(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, cdh={"type": "wrong"}).toGA())

    def test_bad_allow_list(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(*FidoRequest(GARes, allow_list={"type": "wrong"}).toGA())

    def test_bad_allow_list_item(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(
                *FidoRequest(
                    GARes, allow_list=["wrong"] + GARes.request.allow_list
                ).toGA()
            )

    def test_unknown_option(self, device, GARes):
        device.sendGA(*FidoRequest(GARes, options={"unknown": True}).toGA())

    @pytest.mark.skipif('trezor' in sys.argv, reason="User verification flag is intentionally set to true on Trezor even when user verification is not configured. (Otherwise some services refuse registration without giving a reason.)")
    def test_option_uv(self, device, info, GARes):
        if "uv" in info.options:
            if info.options["uv"]:
                res = device.sendGA(*FidoRequest(GARes, options={"uv": True}).toGA())
                assert res.auth_data.flags & (1 << 2)

    def test_option_up(self, device, info, GARes):
        if "up" in info.options:
            if info.options["up"]:
                res = device.sendGA(*FidoRequest(GARes, options={"up": True}).toGA())
                assert res.auth_data.flags & (1 << 0)

    def test_allow_list_fake_item(self, device, GARes):
        device.sendGA(
            *FidoRequest(
                GARes,
                allow_list=[{"type": "rot13", "id": b"1234"}]
                + GARes.request.allow_list,
            ).toGA()
        )

    def test_allow_list_missing_field(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(
                *FidoRequest(
                    GARes, allow_list=[{"id": b"1234"}] + GARes.request.allow_list
                ).toGA()
            )

    def test_allow_list_field_wrong_type(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(
                *FidoRequest(
                    GARes,
                    allow_list=[{"type": b"public-key", "id": b"1234"}]
                    + GARes.request.allow_list,
                ).toGA()
            )

    def test_allow_list_id_wrong_type(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(
                *FidoRequest(
                    GARes,
                    allow_list=[{"type": "public-key", "id": 42}]
                    + GARes.request.allow_list,
                ).toGA()
            )

    def test_allow_list_missing_id(self, device, GARes):
        with pytest.raises(CtapError) as e:
            device.sendGA(
                *FidoRequest(
                    GARes,
                    allow_list=[{"type": "public-key"}] + GARes.request.allow_list,
                ).toGA()
            )

    def test_user_presence_option_false(self, device, MCRes, GARes):
        from cryptography.exceptions import InvalidSignature
        res = device.sendGA(*FidoRequest(GARes, options = {'up': False}).toGA())

        try:
            verify(MCRes, res, GARes.request.cdh)
        except InvalidSignature:
            if 'trezor' not in sys.argv:
                raise

        if '--nfc' not in sys.argv:
            assert((res.auth_data.flags & 1) == 0)


@pytest.mark.skipif('trezor' in sys.argv, reason="Reboot is not supported on Trezor.")
class TestGetAssertionAfterBoot(object):
    def test_assertion_after_reboot(self, rebootedDevice, MCRes, GARes):
        credential_data = AttestedCredentialData(MCRes.auth_data.credential_data)
        verify(MCRes, GARes)
