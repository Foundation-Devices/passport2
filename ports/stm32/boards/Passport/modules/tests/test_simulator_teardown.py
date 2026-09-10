# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import signal
import socket
import subprocess
import sys

from fixtures.simulator import SimulatorSocket


def test_close_kills_unresponsive_process_and_cleans_up(tmp_path):
    connection = SimulatorSocket.__new__(SimulatorSocket)
    connection.simulator_dir = str(tmp_path)
    connection.UNIX_SOCKET_PATH = str(tmp_path / 'server.sock')
    connection.socket_path = str(tmp_path / 'client.sock')
    connection.pipe = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    connection.pipe.bind(connection.socket_path)
    pipe = connection.pipe
    server_path = tmp_path / 'server.sock'
    server_path.touch()
    flash_path = tmp_path / connection.TEST_SPI_FLASH_PATH
    flash_path.parent.mkdir()
    flash_path.touch()

    process = subprocess.Popen(
        [sys.executable, '-c',
         'import signal; signal.signal(signal.SIGTERM, signal.SIG_IGN); '
         'print("ready", flush=True); signal.pause()'],
        stdout=subprocess.PIPE, start_new_session=True,
    )
    connection.process = process
    try:
        assert process.stdout.readline() == b'ready\n'
        connection.close()

        assert process.returncode == -signal.SIGKILL
        assert connection.process is None
        assert pipe.fileno() == -1
        assert not (tmp_path / 'client.sock').exists()
        assert not server_path.exists()
        assert not flash_path.exists()
        connection.close()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        pipe.close()
