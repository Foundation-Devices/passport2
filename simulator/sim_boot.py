# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# NOTE: This code doesn't ship on the official builds of the Passport, this is
# used only for the simulator and for unit testing.

import sys
import uio as io


class SimulatorSocket:
    UNIX_SOCKET_PATH = b'/tmp/passport-simulator.sock'

    def __init__(self):
        self.pipe = None
        self._open()

    def _open(self):
        import sys
        import usocket as socket
        import uerrno as errno
        import ustruct as struct

        self.pipe = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        addr = struct.pack('H108s', socket.AF_UNIX, self.UNIX_SOCKET_PATH)
        while True:
            try:
                self.pipe.bind(addr)
                break
            except OSError as e:
                if e.args[0] == errno.EADDRINUSE:
                    import os
                    os.remove(self.UNIX_SOCKET_PATH)
                    continue
        self.pipe.setblocking(1)

    def recv(self):
        print("Waiting for packet")
        packet_len, sender0 = self.pipe.recvfrom(4)
        packet_len = int.from_bytes(packet_len, 'big')
        assert packet_len >= 4
        print("Received packet of length: {}".format(packet_len))

        packet, sender1 = self.pipe.recvfrom(packet_len)
        assert len(packet) == packet_len
        assert sender0 == sender1

        cmd = packet[0:4]
        text = packet[4:len(packet)].decode('utf-8', 'strict')

        return cmd, text, sender0

    def sendto(self, address, cmd, buf):
        cmd_bytes = cmd.encode('utf-8')
        packet_len = len(cmd_bytes) + len(buf)

        self.pipe.sendto(packet_len.to_bytes(4, 'big'), address)
        self.pipe.sendto(cmd_bytes + buf, address)


def simulator_socket_task():
    print("Starting socket on: {}".format(SimulatorSocket.UNIX_SOCKET_PATH.decode('utf-8', 'strict')))
    socket = SimulatorSocket()

    while True:
        cmd, text, sender = socket.recv()
        print("Sender: {}".format(sender))

        try:
            if cmd == b'exec':
                return_value = io.BytesIO()
                exec(text, dict(return_value=return_value))
                socket.sendto(sender, 'resp', return_value.getvalue())
            else:
                raise Exception("Unknown command")
        except BaseException as e:
            value = io.StringIO()
            sys.print_exception(e, value)
            socket.sendto(sender, 'excp', value.getvalue().encode('utf-8'))


if '--unit-test' in sys.argv:
    simulator_socket_task()
else:
    import main
