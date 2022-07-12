import pytest
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fido2.ctap import CtapError
from fido2.utils import hmac_sha256, sha256

from tests.utils import FidoRequest, shannon_entropy, verify, generate_user


def get_salt_params(cipher, shared_secret, salts):
    enc = cipher.encryptor()
    salt_enc = b""
    for salt in salts:
        salt_enc += enc.update(salt)
    salt_enc += enc.finalize()

    salt_auth = hmac_sha256(shared_secret, salt_enc)[:16]
    return salt_enc, salt_auth


salt1 = b"\xa5" * 32
salt2 = b"\x96" * 32
salt3 = b"\x03" * 32
salt4 = b"\x5a" * 16
salt5 = b"\x96" * 64


@pytest.fixture(scope="class")
def MCHmacSecret(resetDevice,):
    req = FidoRequest(extensions={"hmac-secret": True}, options={"rk": True})
    res = resetDevice.sendMC(*req.toMC())
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="class")
def sharedSecret(device, MCHmacSecret):
    return device.client.pin_protocol.get_shared_secret()


@pytest.fixture(scope="class")
def cipher(device, sharedSecret):
    key_agreement, shared_secret = sharedSecret
    return Cipher(
        algorithms.AES(shared_secret), modes.CBC(b"\x00" * 16), default_backend()
    )

@pytest.fixture(scope="class")
def fixed_users():
    """ Fixed set of users to enable accounts to get overwritten """
    return [ generate_user() for i in range(0, 100) ]


class TestHmacSecret(object):
    def test_hmac_secret_make_credential(self, MCHmacSecret):
        assert MCHmacSecret.auth_data.extensions
        assert "hmac-secret" in MCHmacSecret.auth_data.extensions
        assert MCHmacSecret.auth_data.extensions["hmac-secret"] == True

    def test_hmac_secret_info(self, info):
        assert "hmac-secret" in info.extensions

    def test_fake_extension(self, device):
        req = FidoRequest(extensions={"tetris": True})
        res = device.sendMC(*req.toMC())

    def test_get_shared_secret(self, sharedSecret):
        pass

    @pytest.mark.parametrize("salts", [(salt1,), (salt1, salt2)])
    def test_hmac_secret_entropy(self, device, MCHmacSecret, cipher, sharedSecret, salts):
        key_agreement, shared_secret = sharedSecret
        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, salts)
        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}}
        )
        auth = device.sendGA(*req.toGA())

        ext = auth.auth_data.extensions
        assert ext
        assert "hmac-secret" in ext
        assert isinstance(ext["hmac-secret"], bytes)
        assert len(ext["hmac-secret"]) == len(salts) * 32

        verify(MCHmacSecret, auth, req.cdh)

        dec = cipher.decryptor()
        key = dec.update(ext["hmac-secret"]) + dec.finalize()

        print(shannon_entropy(ext["hmac-secret"]))
        if len(salts) == 1:
            assert shannon_entropy(ext["hmac-secret"]) > 4
            assert shannon_entropy(key) > 4
        if len(salts) == 2:
            assert shannon_entropy(ext["hmac-secret"]) > 5
            assert shannon_entropy(key) > 5

    def get_output(self, device, MCHmacSecret, cipher, sharedSecret, salts):
        key_agreement, shared_secret = sharedSecret
        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, salts)
        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}}
        )
        auth = device.sendGA(*req.toGA())

        ext = auth.auth_data.extensions
        assert ext
        assert "hmac-secret" in ext
        assert isinstance(ext["hmac-secret"], bytes)
        assert len(ext["hmac-secret"]) == len(salts) * 32

        verify(MCHmacSecret, auth, req.cdh)

        dec = cipher.decryptor()
        output = dec.update(ext["hmac-secret"]) + dec.finalize()

        if len(salts) == 2:
            return (output[0:32], output[32:64])
        else:
            return output

    def test_hmac_secret_sanity(self, device, MCHmacSecret, cipher, sharedSecret):
        output1 = self.get_output(device, MCHmacSecret, cipher, sharedSecret, (salt1,))
        output12 = self.get_output(device, MCHmacSecret, cipher, sharedSecret, (salt1, salt2))
        output21 = self.get_output(device, MCHmacSecret, cipher, sharedSecret, (salt2, salt1))

        assert output12[0] == output1
        assert output21[1] == output1
        assert output21[0] == output12[1]
        assert output12[0] != output12[1]

    def test_missing_keyAgreement(self, device, cipher, sharedSecret):
        key_agreement, shared_secret = sharedSecret

        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, (salt3,))

        req = FidoRequest(extensions={"hmac-secret": {2: salt_enc, 3: salt_auth}})

        with pytest.raises(CtapError):
            device.sendGA(*req.toGA())

    def test_missing_saltAuth(self, device, cipher, sharedSecret):
        key_agreement, shared_secret = sharedSecret

        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, (salt3,))

        req = FidoRequest(extensions={"hmac-secret": {1: key_agreement, 2: salt_enc}})

        with pytest.raises(CtapError) as e:
            device.sendGA(*req.toGA())
        assert e.value.code == CtapError.ERR.MISSING_PARAMETER

    def test_missing_saltEnc(self, device, cipher, sharedSecret):
        key_agreement, shared_secret = sharedSecret

        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, (salt3,))

        req = FidoRequest(extensions={"hmac-secret": {1: key_agreement, 3: salt_auth}})

        with pytest.raises(CtapError) as e:
            device.sendGA(*req.toGA())
        assert e.value.code == CtapError.ERR.MISSING_PARAMETER

    def test_bad_auth(self, device, cipher, sharedSecret):

        key_agreement, shared_secret = sharedSecret

        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, (salt3,))

        bad_auth = list(salt_auth[:])
        bad_auth[len(bad_auth) // 2] = bad_auth[len(bad_auth) // 2] ^ 1
        bad_auth = bytes(bad_auth)

        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: bad_auth}}
        )

        with pytest.raises(CtapError) as e:
            device.sendGA(*req.toGA())
        assert e.value.code == CtapError.ERR.EXTENSION_FIRST

    @pytest.mark.parametrize("salts", [(salt4,), (salt4, salt5)])
    def test_invalid_salt_length(self, device, cipher, sharedSecret, salts):
        key_agreement, shared_secret = sharedSecret
        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, salts)

        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}}
        )

        with pytest.raises(CtapError) as e:
            device.sendGA(*req.toGA())
        assert e.value.code == CtapError.ERR.INVALID_LENGTH

    @pytest.mark.skipif('trezor' in sys.argv, reason="Trezor does not support get_next_assertion() because it has a display.")
    @pytest.mark.parametrize("salts", [(salt1,), (salt1, salt2)])
    def test_get_next_assertion_has_extension(self, device, MCHmacSecret, cipher, sharedSecret, salts, fixed_users):
        """ Check that get_next_assertion properly returns extension information for multiple accounts. """
        accounts = 3
        regs = []
        auths = []
        rp = {"id": "example_2.org", "name": "ExampleRP_2"}

        for i in range(0, accounts):
            req = FidoRequest(extensions={"hmac-secret": True},
                              options={"rk": True},
                              rp = rp,
                              user = fixed_users[i])
            res = device.sendMC(*req.toMC())
            regs.append(res)

        key_agreement, shared_secret = sharedSecret
        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, salts)
        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}},
            rp = rp,
        )

        auth = device.sendGA(*req.toGA())
        assert auth.number_of_credentials == accounts

        auths.append(auth)
        for i in range(0, accounts - 1):
            auths.append(device.ctap2.get_next_assertion())

        for x in auths:
            assert x.auth_data.flags & (1 << 7)       # has extension
            ext = auth.auth_data.extensions
            assert ext
            assert "hmac-secret" in ext
            assert isinstance(ext["hmac-secret"], bytes)
            assert len(ext["hmac-secret"]) == len(salts) * 32
            dec = cipher.decryptor()
            key = dec.update(ext["hmac-secret"]) + dec.finalize()

        auths.reverse()
        for x, y in zip(regs, auths):
            verify(x, y, req.cdh)


@pytest.mark.skipif('trezor' in sys.argv, reason="ClientPin is not supported on Trezor.")
class TestHmacSecretUV(object):
    def test_hmac_secret_different_with_uv(self, device, MCHmacSecret, cipher, sharedSecret):
        salts = [salt1]
        key_agreement, shared_secret = sharedSecret
        salt_enc, salt_auth = get_salt_params(cipher, shared_secret, salts)
        req = FidoRequest(
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}}
        )
        auth_no_uv = device.sendGA(*req.toGA())
        assert (auth_no_uv.auth_data.flags & (1<<2)) == 0

        ext_no_uv = auth_no_uv.auth_data.extensions
        assert ext_no_uv
        assert "hmac-secret" in ext_no_uv
        assert isinstance(ext_no_uv["hmac-secret"], bytes)
        assert len(ext_no_uv["hmac-secret"]) == len(salts) * 32

        verify(MCHmacSecret, auth_no_uv, req.cdh)

        # Now get same auth with UV
        pin = '1234'
        device.client.pin_protocol.set_pin(pin)
        pin_token = device.client.pin_protocol.get_pin_token(pin)
        pin_auth = hmac_sha256(pin_token, req.cdh)[:16]

        req = FidoRequest(
            req,
            pin_protocol = 1,
            pin_auth = pin_auth,
            extensions={"hmac-secret": {1: key_agreement, 2: salt_enc, 3: salt_auth}}
        )

        auth_uv = device.sendGA(*req.toGA())
        assert auth_uv.auth_data.flags & (1<<2)
        ext_uv = auth_uv.auth_data.extensions
        assert ext_uv
        assert "hmac-secret" in ext_uv
        assert isinstance(ext_uv["hmac-secret"], bytes)
        assert len(ext_uv["hmac-secret"]) == len(salts) * 32

        verify(MCHmacSecret, auth_uv, req.cdh)

        # Now see if the hmac-secrets are different
        assert ext_no_uv['hmac-secret'] != ext_uv['hmac-secret']

