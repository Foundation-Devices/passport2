import pytest
from fido2.ctap import CtapError
from fido2.ctap2 import ES256, AttestedCredentialData, PinProtocolV1
from fido2.utils import hmac_sha256, sha256

from tests.utils import FidoRequest


# Test U2F register works with FIDO2 auth
class TestCtap1WithCtap2(object):
    def test_ctap1_register(self, RegRes):
        RegRes.verify(RegRes.request.appid, RegRes.request.challenge)

    def test_ctap1_authenticate(self, RegRes, AuthRes):
        AuthRes.verify(
            AuthRes.request.appid, AuthRes.request.challenge, RegRes.public_key
        )

    def test_authenticate_ctap1_through_ctap2(self, device, RegRes):
        req = FidoRequest(allow_list=[{"id": RegRes.key_handle, "type": "public-key"}])

        auth = device.sendGA(*req.toGA())

        credential_data = AttestedCredentialData.from_ctap1(
            RegRes.key_handle, RegRes.public_key
        )
        auth.verify(req.cdh, credential_data.public_key)
        assert auth.credential["id"] == RegRes.key_handle

# Test FIDO2 register works with U2F auth
class TestCtap2WithCtap1(object):
    def test_ctap1_authenticate(self, MCRes, device):
        req = FidoRequest()
        key_handle = MCRes.auth_data.credential_data.credential_id
        res = device.authenticate(req.challenge, req.appid, key_handle)

        credential_data = AttestedCredentialData(MCRes.auth_data.credential_data)
        pubkey_string = b'\x04' + credential_data.public_key[-2] + credential_data.public_key[-3]

        res.verify(
            req.appid, req.challenge, pubkey_string
        )