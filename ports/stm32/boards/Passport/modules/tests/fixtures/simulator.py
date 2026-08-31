# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import os
import signal
import time


class SimulatorSocket:
    UNIX_SOCKET_PATH = b'/tmp/passport-simulator.sock'

    def __init__(self, simulator_dir):
        self.pipe = None
        self.process = None
        self.socket_path = None
        try:
            self._open(simulator_dir)
            self._connect()
        except BaseException:
            self.close()
            raise

    def _open(self, simulator_dir):
        import subprocess

        simulator_cmd = simulator_dir + '/simulator.py'
        self.process = subprocess.Popen([simulator_cmd, 'color', '--unit-test'], cwd=simulator_dir,
                                        preexec_fn=os.setsid)

    def _connect(self):
        import socket
        import tempfile

        self.pipe = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        deadline = time.monotonic() + 10
        while True:
            try:
                self.pipe.connect(self.UNIX_SOCKET_PATH)
                break
            except OSError:
                if self.process.poll() is not None:
                    raise RuntimeError(
                        'Simulator exited before opening its socket '
                        f'(exit code {self.process.returncode})'
                    )
                if time.monotonic() >= deadline:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    raise TimeoutError('Simulator did not open its socket within 10 seconds')
                time.sleep(0.01)

        while True:
            try:
                with tempfile.NamedTemporaryFile(suffix='.sock', prefix='passport-client.',
                                                 dir='/tmp', delete=True) as tmpfile:
                    addr = tmpfile.name
                self.pipe.bind(addr)
                self.socket_path = addr
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Could not bind the simulator client socket within 10 seconds') from error
                time.sleep(0.01)

    # Close the connection and kill the simulator process.
    def close(self):
        if self.pipe is not None:
            self.pipe.close()
            self.pipe = None
        if self.socket_path is not None:
            try:
                os.unlink(self.socket_path)
            except FileNotFoundError:
                pass
            self.socket_path = None
        if self.process is not None and self.process.poll() is None:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    # Run `exec()` in the Unix MP simulator.
    def exec(self, object):
        return self.execute_command('exec', object)

    # Execute a command in the Unix MP simulator.
    def execute_command(self, cmd, text):
        cmd_bytes = cmd.encode('utf-8')
        text_bytes = text.encode('utf-8')
        packet_len = len(cmd_bytes) + len(text_bytes)

        self.pipe.send(packet_len.to_bytes(length=4, byteorder='big'))
        self.pipe.send(cmd_bytes + text_bytes)

        self.pipe.settimeout(5)
        packet_len_bytes = self.pipe.recv(4)
        packet_len = int.from_bytes(packet_len_bytes, byteorder='big')

        packet = self.pipe.recv(packet_len)
        self.pipe.settimeout(0)

        cmd = packet[0:4].decode('utf-8', 'strict')
        buf = packet[4:len(packet)]

        return cmd, buf


# Get a connection to the simulator.
@pytest.fixture
def simulator(simulatordir):
    connection = SimulatorSocket(simulatordir)
    try:
        yield connection
    finally:
        connection.close()


# Execute a file in the simulator using the Unix Micro-Python built-in `exec()` function.
@pytest.fixture
def exec_file(simulator):
    def doit(filename):
        from pathlib import Path
        cmd, return_value = simulator.exec(Path(filename).read_text())
        if cmd == 'excp':
            pytest.fail('Remote test failed with exception:\n{}'.format(return_value.decode('utf-8', 'strict')))
        elif cmd == 'resp':
            return return_value
        else:
            pytest.fail('Unknown response command')

    return doit
