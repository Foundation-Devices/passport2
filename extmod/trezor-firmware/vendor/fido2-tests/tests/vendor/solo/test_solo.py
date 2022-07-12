import sys

import pytest
from fido2.ctap1 import ApduError
from fido2.ctap2 import CtapError
from fido2.utils import sha256
from solo.client import SoloClient
from solo.commands import SoloExtension

from tests.utils import shannon_entropy, verify, FidoRequest


@pytest.fixture(scope="module", params=["u2f"])
def solo(request, device):
    sc = SoloClient()
    sc.find_device(device.dev)
    if request.param == "u2f":
        sc.use_u2f()
    else:
        sc.use_hid()
    return sc

IS_EXPERIMENTAL = '--experimental' in sys.argv
IS_NFC = '--nfc' in sys.argv

@pytest.mark.skipif(
    IS_NFC,
    reason="Wrong transport"
)
class TestSolo(object):
    def test_solo(self, solo):
        pass

    def test_rng(self, solo):

        total = 1024 * 16
        entropy = b""
        while len(entropy) < total:
            entropy += solo.get_rng()

        s = shannon_entropy(entropy)
        assert s > 7.98
        print("Entropy is %.5f bits per byte." % s)

    def test_version(self, solo):
        assert len(solo.solo_version()) == 4

    def test_version_hid(self, solo):
        data = solo.send_data_hid(0x61, b'')
        assert len(data) == 4
        print(f'Version is {data[0]}.{data[1]}.{data[2]} locked?=={data[3]}')


    def test_bootloader_not(self, solo):
        with pytest.raises(ApduError) as e:
            solo.write_flash(0x0, b"1234")

    def test_fido2_bridge(self, solo):
        exchange = solo.exchange
        solo.exchange = solo.exchange_fido2

        req = SoloClient.format_request(SoloExtension.version, 0, b"A" * 16)
        a = solo.ctap2.get_assertion(
            solo.host, b"B" * 32, [{"id": req, "type": "public-key"}]
        )

        assert a.auth_data.rp_id_hash == sha256(solo.host.encode("utf8"))
        assert a.credential["id"] == req
        assert (a.auth_data.flags & 0x5) == 0x5

        solo.get_rng()

        solo.exchange = exchange

    @pytest.mark.skipif(not IS_EXPERIMENTAL, reason="Experimental")
    def test_load_external_key_wrong_length(self,solo, ):
        ext_key_cmd = 0x62
        with pytest.raises(CtapError) as e:
            solo.send_data_hid(ext_key_cmd, b'\x01\x00\x00\x00' + b'wrong length'*2)
        assert(e.value.code == CtapError.ERR.INVALID_LENGTH)

    @pytest.mark.skipif(not IS_EXPERIMENTAL, reason="Experimental")
    def test_load_external_key_invalidate_old_cred(self,solo, device, MCRes, GARes):
        ext_key_cmd = 0x62
        verify(MCRes, GARes)
        print ('Enter user presence THREE times.')
        solo.send_data_hid(ext_key_cmd, b'\x01\x00\x00\x00' + b'Z' * 96)

        # Old credential should not exist now.
        with pytest.raises(CtapError) as e:
            ga_bad_req = FidoRequest(GARes)
            device.sendGA(*ga_bad_req.toGA())
        assert(e.value.code == CtapError.ERR.NO_CREDENTIALS)


    @pytest.mark.skipif(not IS_EXPERIMENTAL, reason="Experimental")
    def test_load_external_key(self,solo, device,):
        
        key_A = b'A' * 96
        key_B = b'B' * 96
        ext_key_cmd = 0x62
        print ('Enter user presence THREE times.')
        solo.send_data_hid(ext_key_cmd, b'\x01\x00\x00\x00' + key_A)

        # New credential works.
        mc_A_req = FidoRequest()
        mc_A_res = device.sendMC(*mc_A_req.toMC())

        allow_list = [{"id":mc_A_res.auth_data.credential_data.credential_id, "type":"public-key"}]
        ga_A_req = FidoRequest(mc_A_req, allow_list=allow_list)
        ga_A_res = device.sendGA(*FidoRequest(ga_A_req).toGA())

        verify(mc_A_res, ga_A_res, ga_A_req.cdh)

        # Load up Key B and verify cred A doesn't exist.
        print ('Enter user presence THREE times.')
        solo.send_data_hid(ext_key_cmd, b'\x01\x00\x00\x00' + key_B)
        with pytest.raises(CtapError) as e:
            ga_A_res = device.sendGA(*FidoRequest(ga_A_req).toGA())
        assert(e.value.code == CtapError.ERR.NO_CREDENTIALS)

        # Load up Key A and verify cred A is back.
        print ('Enter user presence THREE times.')
        solo.send_data_hid(ext_key_cmd, b'\x01\x00\x00\x00' + key_A)
        ga_A_res = device.sendGA(*FidoRequest(ga_A_req).toGA())
        verify(mc_A_res, ga_A_res, ga_A_req.cdh)

