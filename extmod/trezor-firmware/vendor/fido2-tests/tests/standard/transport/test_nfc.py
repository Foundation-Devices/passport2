import sys
import pytest

from tests.utils import FidoRequest


@pytest.mark.skipif(
    not ('--nfc' in sys.argv),
    reason="NFC transport only"
)
class TestMakeCredential(object):
    def test_big_request_response(self, device, MCRes):
        req = FidoRequest(
            MCRes,
            exclude_list=[
                {
                    "id": b"0123456789012345678901234567890123456789012345678901234567890123456789",
                    "type": "public-key"},
                {
                    "id": b"1123456789012345678901234567890123456789012345678901234567890123456789",
                    "type": "public-key"},
                {
                    "id": b"2123456789012345678901234567890123456789012345678901234567890123456789",
                    "type": "public-key"}],
        )
        device.sendMC(*req.toMC())
