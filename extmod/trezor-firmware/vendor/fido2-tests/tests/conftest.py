import struct
import time
import sys

import pytest
from fido2.attestation import Attestation
from fido2.client import Fido2Client, _call_polling
from fido2.ctap import CtapError
from fido2.ctap1 import CTAP1
from fido2.ctap2 import ES256, AttestedCredentialData, PinProtocolV1
from fido2.hid import CtapHidDevice
from fido2.utils import hmac_sha256, sha256

from tests.utils import *

if 'trezor' in sys.argv:
    from .vendor.trezor.udp_backend import force_udp_backend
else:
    from solo.fido2 import force_udp_backend


def pytest_addoption(parser):
    parser.addoption("--sim", action="store_true")
    parser.addoption("--nfc", action="store_true")
    parser.addoption("--experimental", action="store_true")
    parser.addoption("--vendor", default="none")


@pytest.fixture()
def is_simulation(pytestconfig):
    return pytestconfig.getoption("sim")


@pytest.fixture()
def is_nfc(pytestconfig):
    return pytestconfig.getoption("nfc")


@pytest.fixture(scope="module")
def info(device):
    info = device.ctap2.get_info()
    # print("data:", bytes(info))
    # print("decoded:", cbor.decode_from(bytes(info)))
    return info


@pytest.fixture(scope="module")
def MCRes(resetDevice,):
    req = FidoRequest()
    res = resetDevice.sendMC(*req.toMC())
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="class")
def GARes(device, MCRes):
    req = FidoRequest(
        allow_list=[
            {"id": MCRes.auth_data.credential_data.credential_id, "type": "public-key"}
        ]
    )
    res = device.sendGA(*req.toGA())
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="module")
def RegRes(resetDevice,):
    req = FidoRequest()
    res = resetDevice.register(req.challenge, req.appid)
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="class")
def AuthRes(device, RegRes):
    req = FidoRequest()
    res = device.authenticate(req.challenge, req.appid, RegRes.key_handle)
    setattr(res, "request", req)
    return res


@pytest.fixture(scope="module")
def allowListItem(MCRes):
    return


@pytest.fixture(scope="session")
def device(pytestconfig):
    if pytestconfig.getoption("sim"):
        print("FORCE UDP")
        force_udp_backend()

    dev = TestDevice()
    dev.set_sim(pytestconfig.getoption("sim"))

    dev.find_device(pytestconfig.getoption("nfc"))

    return dev


@pytest.fixture(scope="class")
def rebootedDevice(device):
    device.reboot()
    return device


@pytest.fixture(scope="module")
def resetDevice(device):
    device.reset()
    return device


class Packet(object):
    def __init__(self, data):
        self.data = data

    def ToWireFormat(self,):
        return self.data

    @staticmethod
    def FromWireFormat(pkt_size, data):
        return Packet(data)


class TestDevice:
    def __init__(self, tester=None):
        self.origin = "https://examplo.org"
        self.host = "examplo.org"
        self.user_count = 10
        self.is_sim = False
        self.is_nfc = False
        self.nfc_interface_only = False
        if tester:
            self.initFrom(tester)

    def initFrom(self, tester):
        self.user_count = tester.user_count
        self.is_sim = tester.is_sim
        self.is_nfc = tester.is_nfc
        self.dev = tester.dev
        self.ctap2 = tester.ctap2
        self.ctap1 = tester.ctap1
        self.client = tester.client
        self.nfc_interface_only = tester.nfc_interface_only

    def find_device(self, nfcInterfaceOnly=False):
        dev = None
        self.nfc_interface_only = nfcInterfaceOnly
        if not nfcInterfaceOnly:
            # print("--- HID ---")
            # print(list(CtapHidDevice.list_devices()))
            dev = next(CtapHidDevice.list_devices(), None)

        if not dev:
            from fido2.pcsc import CtapPcscDevice

            # print("--- NFC ---")
            # print(list(CtapPcscDevice.list_devices()))
            dev = next(CtapPcscDevice.list_devices(), None)
            if dev:
                self.is_nfc = True

        if not dev:
            raise RuntimeError("No FIDO device found")
        self.dev = dev
        self.client = Fido2Client(dev, self.origin)
        self.ctap2 = self.client.ctap2
        self.ctap1 = CTAP1(dev)

        # consume timeout error
        # cmd,resp = self.recv_raw()

    def set_user_count(self, count):
        self.user_count = count

    def set_sim(self, b):
        self.is_sim = b

    def reboot(self,):
        if self.is_sim:
            print("Sending restart command...")
            self.send_magic_reboot()
            TestDevice.delay(0.25)
            return

        if self.is_nfc:
            if self.send_nfc_reboot():
                TestDevice.delay(0.5)
                self.find_device(self.nfc_interface_only)
                return

        if 'solokeys' in sys.argv:
            try:
                self.dev.call(0x53 ^ 0x80,b'')
            except OSError:
                pass

            print('Rebooting..')
            for _ in range(0,8):
                time.sleep(0.1)
                try:
                    self.find_device(self.nfc_interface_only)
                    return
                except RuntimeError:
                    pass
        else:
            print("Please reboot authenticator and hit enter")
            input()
            self.find_device(self.nfc_interface_only)

    def send_data(self, cmd, data):
        if not isinstance(data, bytes):
            data = struct.pack("%dB" % len(data), *[ord(x) for x in data])
        with Timeout(1.0) as event:
            event.is_set()
            return self.dev.call(cmd, data, event)

    def send_raw(self, data, cid=None):
        if cid is None:
            cid = self.dev._dev.cid
        elif not isinstance(cid, bytes):
            cid = struct.pack("%dB" % len(cid), *[ord(x) for x in cid])
        if not isinstance(data, bytes):
            data = struct.pack("%dB" % len(data), *[ord(x) for x in data])
        data = cid + data
        l = len(data)
        if l != 64:
            pad = "\x00" * (64 - l)
            pad = struct.pack("%dB" % len(pad), *[ord(x) for x in pad])
            data = data + pad
        data = list(data)
        assert len(data) == 64
        self.dev._dev.InternalSendPacket(Packet(data))

    def send_magic_reboot(self,):
        """
        For use in simulation and testing.  Random bytes that authenticator should detect
        and then restart itself.
        """
        magic_cmd = (
            b"\xac\x10\x52\xca\x95\xe5\x69\xde\x69\xe0\x2e\xbf"
            + b"\xf3\x33\x48\x5f\x13\xf9\xb2\xda\x34\xc5\xa8\xa3"
            + b"\x40\x52\x66\x97\xa9\xab\x2e\x0b\x39\x4d\x8d\x04"
            + b"\x97\x3c\x13\x40\x05\xbe\x1a\x01\x40\xbf\xf6\x04"
            + b"\x5b\xb2\x6e\xb7\x7a\x73\xea\xa4\x78\x13\xf6\xb4"
            + b"\x9a\x72\x50\xdc"
        )
        self.dev._dev.InternalSendPacket(Packet(magic_cmd))

    def send_nfc_reboot(self,):
        """
        Send magic nfc reboot sequence for solokey
        """
        data = b"\x12\x56\xab\xf0"
        header = struct.pack('!BBBBB', 0x00, 0xee, 0x00, 0x00, len(data))
        resp, sw1, sw2 = self.dev.apdu_exchange(header + data)
        return sw1 == 0x90 and sw2 == 0x00

    def cid(self,):
        return self.dev._dev.cid

    def set_cid(self, cid):
        if not isinstance(cid, (bytes, bytearray)):
            cid = struct.pack("%dB" % len(cid), *[ord(x) for x in cid])
        self.dev._dev.cid = cid

    def recv_raw(self,):
        with Timeout(1.0):
            cmd, payload = self.dev._dev.InternalRecv()
        return cmd, payload

    def check_error(data, err=None):
        assert len(data) == 1
        if err is None:
            if data[0] != 0:
                raise CtapError(data[0])
        elif data[0] != err:
            raise ValueError("Unexpected error: %02x" % data[0])

    def register(self, chal, appid, on_keepalive=DeviceSelectCredential(1)):
        reg_data = _call_polling(0.25, None, on_keepalive, self.ctap1.register, chal, appid)
        return reg_data

    def authenticate(self, chal, appid, key_handle, check_only=False, on_keepalive=DeviceSelectCredential(1)):
        auth_data = _call_polling(
            0.25,
            None,
            on_keepalive,
            self.ctap1.authenticate,
            chal,
            appid,
            key_handle,
            check_only=check_only,
        )
        return auth_data

    def reset(self,):
        print("Resetting Authenticator...")
        try:
            self.ctap2.reset(on_keepalive=DeviceSelectCredential(1))
        except CtapError:
            # Some authenticators need a power cycle
            print("You must power cycle authentictor.  Hit enter when done.")
            input()
            time.sleep(0.2)
            self.find_device(self.nfc_interface_only)
            self.ctap2.reset(on_keepalive=DeviceSelectCredential(1))

    def sendMC(self, *args, **kwargs):
        attestation_object = self.ctap2.make_credential(*args, **kwargs)
        if attestation_object:
            verifier = Attestation.for_type(attestation_object.fmt)
            client_data = args[0]
            verifier().verify(
                attestation_object.att_statement,
                attestation_object.auth_data,
                client_data,
            )
        return attestation_object

    def sendGA(self, *args, **kwargs):
        return self.ctap2.get_assertion(*args, **kwargs)

    def sendCP(self, *args, **kwargs):
        return self.ctap2.client_pin(*args, **kwargs)

    def sendPP(self, *args, **kwargs):
        return self.client.pin_protocol.get_pin_token(*args, **kwargs)

    def delay(secs):
        time.sleep(secs)
