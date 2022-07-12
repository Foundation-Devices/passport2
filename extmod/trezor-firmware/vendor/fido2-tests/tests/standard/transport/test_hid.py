import os
import socket
import sys
import time
from binascii import hexlify

import pytest
from fido2.ctap import CtapError
from fido2.hid import CAPABILITY, CTAPHID

check_timeouts = 'trezor' in sys.argv

@pytest.mark.skipif(
    '--nfc' in sys.argv,
    reason="Wrong transport"
)
class TestHID(object):
    def test_long_ping(self, device):
        amt = 1000
        pingdata = os.urandom(amt)

        t1 = time.time() * 1000
        r = device.send_data(CTAPHID.PING, pingdata)
        t2 = time.time() * 1000
        delt = t2 - t1

        assert not (delt > 555 * (amt / 1000))

        assert r == pingdata

    def test_init(self, device):
        if check_timeouts:
            with pytest.raises(socket.timeout):
                cmd, resp = device.recv_raw()

        payload = b"\x11\x11\x11\x11\x11\x11\x11\x11"
        r = device.send_data(CTAPHID.INIT, payload)
        print(r)
        assert r[:8] == payload

    def test_ping(self, device):

        pingdata = os.urandom(100)
        r = device.send_data(CTAPHID.PING, pingdata)
        assert r == pingdata

    def test_wink(self, device):
        if device.dev.capabilities & CAPABILITY.WINK:
            r = device.send_data(CTAPHID.WINK, "")

    def test_cbor_no_payload(self, device):
        with pytest.raises(CtapError) as e:
            r = device.send_data(CTAPHID.CBOR, "")
        assert e.value.code == CtapError.ERR.INVALID_LENGTH

    def test_no_data_in_u2f_msg(self, device):
        with pytest.raises(CtapError) as e:
            r = device.send_data(CTAPHID.MSG, "")
            print(hexlify(r))
        assert e.value.code == CtapError.ERR.INVALID_LENGTH

    def test_invalid_hid_cmd(self, device):
        r = device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")

        with pytest.raises(CtapError) as e:
            r = device.send_data(0x66, "")
        assert e.value.code == CtapError.ERR.INVALID_COMMAND

    def test_oversize_packet(self, device):
        device.send_raw("\x81\x1d\xba\x00")
        cmd, resp = device.recv_raw()
        assert resp[0] == CtapError.ERR.INVALID_LENGTH

    def test_skip_sequence_number(self, device):
        r = device.send_data(CTAPHID.PING, "\x44" * 200)
        device.send_raw("\x81\x04\x90")
        device.send_raw("\x00")
        device.send_raw("\x01")
        # skip 2
        device.send_raw("\x03")
        cmd, resp = device.recv_raw()
        assert resp[0] == CtapError.ERR.INVALID_SEQ

    def test_resync_and_ping(self, device):
        r = device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        pingdata = os.urandom(100)
        r = device.send_data(CTAPHID.PING, pingdata)
        if r != pingdata:
            raise ValueError("Ping data not echo'd")

    def test_ping_abort(self, device):
        device.send_raw("\x81\x04\x00")
        device.send_raw("\x00")
        device.send_raw("\x01")
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")

    def test_ping_abort_from_different_cid(self, device):
        oldcid = device.cid()
        newcid = bytes([oldcid[0] ^ 1]) + oldcid[1:]
        device.send_raw("\x81\x10\x00")
        device.send_raw("\x00")
        device.send_raw("\x01")
        device.set_cid(newcid)
        device.send_raw(
            "\x86\x00\x08\x11\x22\x33\x44\x55\x66\x77\x88"
        )  # init from different cid
        print("wait for init response")
        cmd, r = device.recv_raw()  # init response
        assert cmd == 0x86
        device.set_cid(oldcid)
        if check_timeouts:
            # print('wait for timeout')
            cmd, r = device.recv_raw()  # timeout response
            assert cmd == 0xBF

    def test_timeout(self, device):
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        t1 = time.time() * 1000
        device.send_raw("\x81\x04\x00")
        device.send_raw("\x00")
        device.send_raw("\x01")
        cmd, r = device.recv_raw()  # timeout response
        t2 = time.time() * 1000
        delt = t2 - t1
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.TIMEOUT
        assert delt < 1000 and delt > 400

    def test_not_cont(self, device):
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        device.send_raw("\x81\x04\x00")
        device.send_raw("\x00")
        device.send_raw("\x01")
        device.send_raw("\x81\x10\x00")  # init packet
        cmd, r = device.recv_raw()  # timeout response
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.INVALID_SEQ

        if check_timeouts:
            device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
            device.send_raw("\x01\x10\x00")
            with pytest.raises(socket.timeout):
                cmd, r = device.recv_raw()  # timeout response

    def test_check_busy(self, device):
        t1 = time.time() * 1000
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        oldcid = device.cid()
        newcid = bytes([oldcid[0] ^ 1]) + oldcid[1:]
        device.send_raw("\x81\x04\x00")
        device.set_cid(newcid)
        device.send_raw("\x81\x04\x00")
        cmd, r = device.recv_raw()  # busy response
        t2 = time.time() * 1000
        assert t2 - t1 < 100
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.CHANNEL_BUSY

        device.set_cid(oldcid)
        cmd, r = device.recv_raw()  # timeout response
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.TIMEOUT

    def test_check_busy_interleaved(self, device):
        cid1 = "\x11\x22\x33\x44"
        cid2 = "\x01\x22\x33\x44"
        device.set_cid(cid2)
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        device.set_cid(cid1)
        device.send_data(CTAPHID.INIT, "\x11\x22\x33\x44\x55\x66\x77\x88")
        device.send_raw("\x81\x00\x63")  # echo 99 bytes first channel

        device.set_cid(cid2)  # send ping on 2nd channel
        device.send_raw("\x81\x00\x63")
        time.sleep(0.1)
        device.send_raw("\x00")

        cmd, r = device.recv_raw()  # busy response

        device.set_cid(cid1)  # finish 1st channel ping
        device.send_raw("\x00")

        device.set_cid(cid2)

        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.CHANNEL_BUSY

        device.set_cid(cid1)
        cmd, r = device.recv_raw()  # ping response
        assert cmd == 0x81
        assert len(r) == 0x63

    def test_cid_0(self, device):
        device.set_cid("\x00\x00\x00\x00")
        device.send_raw(
            "\x86\x00\x08\x11\x22\x33\x44\x55\x66\x77\x88", cid="\x00\x00\x00\x00"
        )
        cmd, r = device.recv_raw()  # timeout
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.INVALID_CHANNEL
        device.set_cid("\x05\x04\x03\x02")

    def test_cid_ffffffff(self, device):

        device.set_cid("\xff\xff\xff\xff")
        device.send_raw(
            "\x81\x00\x08\x11\x22\x33\x44\x55\x66\x77\x88", cid="\xff\xff\xff\xff"
        )
        cmd, r = device.recv_raw()  # timeout
        assert cmd == 0xBF
        assert r[0] == CtapError.ERR.INVALID_CHANNEL
        device.set_cid("\x05\x04\x03\x02")
