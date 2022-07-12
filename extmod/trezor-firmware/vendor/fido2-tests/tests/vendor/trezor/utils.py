import os
import socket
from fido2.ctap import STATUS

from trezorlib import debuglink
from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.device import wipe as wipe_device
from trezorlib.transport import enumerate_devices, get_transport


def get_device():
    path = os.environ.get("TREZOR_PATH")
    if path:
        try:
            transport = get_transport(path)
            return TrezorClientDebugLink(transport)
        except Exception as e:
            raise RuntimeError("Failed to open debuglink for {}".format(path)) from e

    else:
        devices = enumerate_devices()
        for device in devices:
            try:
                return TrezorClientDebugLink(device)
            except Exception:
                pass
        else:
            raise RuntimeError("No debuggable device found")


def load_client():
    try:
        client = get_device()
    except RuntimeError:
        request.session.shouldstop = "No debuggable Trezor is available"
        pytest.fail("No debuggable Trezor is available")

    wipe_device(client)
    debuglink.load_device_by_mnemonic(
        client,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
        language="en-US",
    )
    client.clear_session()

    client.open()
    return client


TREZOR_CLIENT = load_client()


class DeviceSelectCredential:
    def __init__(self, number=1):
        self.number = number

    def __call__(self, status):
        if status != STATUS.UPNEEDED:
            return

        if self.number == 0:
            TREZOR_CLIENT.debug.press_no()
        else:
            for _ in range(self.number - 1):
                TREZOR_CLIENT.debug.swipe_left()
            TREZOR_CLIENT.debug.press_yes()
