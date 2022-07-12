import os
import socket
import sys

import fido2._pyu2f
import fido2._pyu2f.base


def force_udp_backend():
    fido2._pyu2f.InternalPlatformSwitch = _UDP_InternalPlatformSwitch


def _UDP_InternalPlatformSwitch(funcname, *args, **kwargs):
    if funcname == "__init__":
        return HidOverUDP(*args, **kwargs)
    return getattr(HidOverUDP, funcname)(*args, **kwargs)


def format_pkg(d, p):
    # print(d, " ".join(["%02x" % i for i in p]))
    pass


class HidOverUDP(fido2._pyu2f.base.HidDevice):
    @staticmethod
    def Enumerate():
        TREZOR_FIDO2_UDP_PORT = os.getenv("TREZOR_FIDO2_UDP_PORT", default="21326")
        a = [
            {
                "vendor_id": 0x1209,
                "product_id": 0x53C1,
                "product_string": "TREZOR",
                "serial_number": "12345678",
                "usage": 0x01,
                "usage_page": 0xF1D0,
                "path": "127.0.0.1:%s" % TREZOR_FIDO2_UDP_PORT,
            }
        ]
        return a

    def __init__(self, path):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 7112))
        addr, port = path.split(":")
        port = int(port)
        self.token = (addr, port)
        self.sock.settimeout(2.0)

    def GetInReportDataLength(self):
        return 64

    def GetOutReportDataLength(self):
        return 64

    def Write(self, packet):
        format_pkg(">>>", packet)
        self.sock.sendto(bytearray(packet), self.token)

    def Read(self):
        msg = [0] * 64
        pkt, _ = self.sock.recvfrom(64)
        for i, v in enumerate(pkt):
            try:
                msg[i] = ord(v)
            except TypeError:
                msg[i] = v
        format_pkg("<<<", msg)
        return msg
