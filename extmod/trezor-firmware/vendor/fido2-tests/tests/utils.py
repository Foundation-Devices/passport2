import math
import random
import secrets
import sys
from threading import Event, Timer
from numbers import Number

from fido2.ctap2 import ES256, AttestedCredentialData, PinProtocolV1
from fido2.utils import hmac_sha256, sha256

if 'trezor' in sys.argv:
    from .vendor.trezor.utils import DeviceSelectCredential
else:
    from .vendor.solo.utils import DeviceSelectCredential

name_list = open("data/first-names.txt").readlines()


def shannon_entropy(data):
    s = 0.0
    total = len(data)
    for x in range(0, 256):
        freq = data.count(x)
        p = freq / total
        if p > 0:
            s -= p * math.log2(p)
    return s


def verify(reg, auth, cdh=None):
    credential_data = AttestedCredentialData(reg.auth_data.credential_data)
    if cdh is None:
        cdh = auth.request.cdh
    auth.verify(cdh, credential_data.public_key)
    assert auth.auth_data.rp_id_hash == reg.auth_data.rp_id_hash
    assert auth.credential["id"] == reg.auth_data.credential_data.credential_id


def generate_rp():
    return {"id": "example.org", "name": "ExampleRP"}


def generate_user():

    # https://www.w3.org/TR/webauthn/#user-handle
    user_id_length = random.randint(1, 64)
    user_id = secrets.token_bytes(user_id_length)

    # https://www.w3.org/TR/webauthn/#dictionary-pkcredentialentity
    name = " ".join(random.choice(name_list).strip() for i in range(0, 3))
    icon = "https://www.w3.org/TR/webauthn/"
    display_name = "Displayed " + name

    return {"id": user_id, "name": name, "icon": icon, "displayName": display_name}


counter = 1

def generate_user_maximum():
    """
    Generate RK with the maximum lengths of the fields, according to the minimal requirements of the FIDO2 spec
    """
    global counter

    # https://www.w3.org/TR/webauthn/#user-handle
    user_id_length = 64
    user_id = secrets.token_bytes(user_id_length)

    # https://www.w3.org/TR/webauthn/#dictionary-pkcredentialentity
    name = " ".join(random.choice(name_list).strip() for i in range(0, 30))
    name = f'{counter}: {name}'
    icon = "https://www.w3.org/TR/webauthn/" + 'A'*128
    display_name = "Displayed " + name

    name = name[:64]
    display_name = display_name[:64]
    icon = icon[:128]

    counter += 1

    return {"id": user_id, "name": name, "icon": icon, "displayName": display_name}


def generate_challenge():
    return secrets.token_bytes(32)


def get_key_params():
    return [{"type": "public-key", "alg": ES256.ALGORITHM}]


def generate_cdh():
    return b"123456789abcdef0123456789abcdef0"


def generate(param):
    if param == "rp":
        return generate_rp()
    if param == "user":
        return generate_user()
    if param == "challenge":
        return generate_challenge()
    if param == "cdh":
        return generate_cdh()
    if param == "key_params":
        return get_key_params()
    if param == "allow_list":
        return []
    if param == "on_keepalive":
        return DeviceSelectCredential(1)
    return None


class Empty:
    pass


class FidoRequest:
    def __init__(self, request=None, **kwargs):

        if not isinstance(request, FidoRequest) and request is not None:
            request = request.request

        self.request = request

        for i in (
            "cdh",
            "key_params",
            "allow_list",
            "challenge",
            "rp",
            "user",
            "pin_protocol",
            "options",
            "appid",
            "exclude_list",
            "extensions",
            "pin_auth",
            "timeout",
            "on_keepalive",
        ):
            self.save_attr(i, kwargs.get(i, Empty), request)

        if isinstance(self.rp, dict) and "id" in self.rp:
            if hasattr(self.rp["id"], "encode"):
                self.appid = sha256(self.rp["id"].encode("utf8"))

        # self.chal = sha256(self.challenge.encode("utf8"))

    def save_attr(self, attr, value, request):
        """
            Will assign attribute from source, in following priority:
                Argument, request object, generated
        """
        if value != Empty:
            setattr(self, attr, value)
        elif request is not None:
            setattr(self, attr, getattr(request, attr))
        else:
            setattr(self, attr, generate(attr))

    def toGA(self,):
        return [
            None if not self.rp else self.rp["id"],
            self.cdh,
            self.allow_list,
            self.extensions,
            self.options,
            self.pin_auth,
            self.pin_protocol,
            self.timeout,
            self.on_keepalive,
        ]

    def toMC(self,):
        return [
            self.cdh,
            self.rp,
            self.user,
            self.key_params,
            self.exclude_list,
            self.extensions,
            self.options,
            self.pin_auth,
            self.pin_protocol,
            self.timeout,
            self.on_keepalive,
        ]

        return args + self.get_optional_args()


# Timeout from:
#   https://github.com/Yubico/python-fido2/blob/f1dc028d6158e1d6d51558f72055c65717519b9b/fido2/utils.py
# Copyright (c) 2013 Yubico AB
# All rights reserved.
#
#   Redistribution and use in source and binary forms, with or
#   without modification, are permitted provided that the following
#   conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

class Timeout(object):
    """Utility class for adding a timeout to an event.
    :param time_or_event: A number, in seconds, or a threading.Event object.
    :ivar event: The Event associated with the Timeout.
    :ivar timer: The Timer associated with the Timeout, if any.
    """

    def __init__(self, time_or_event):

        if isinstance(time_or_event, Number):
            self.event = Event()
            self.timer = Timer(time_or_event, self.event.set)
        else:
            self.event = time_or_event
            self.timer = None

    def __enter__(self):
        if self.timer:
            self.timer.start()
        return self.event

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer:
            self.timer.cancel()
            self.timer.join()
