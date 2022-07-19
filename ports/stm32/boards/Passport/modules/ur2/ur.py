# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
# ur.py
#

from .utils import is_ur_type
from .cbor_lite import CBORDecoder, CBOREncoder
from micropython import const

_TAG_UUID = const(37)
_UUID_LEN = const(16)


class URException(Exception):
    pass


class InvalidType(URException):
    pass


class InvalidUuid(URException):
    pass


class InvalidScvChallenge(URException):
    pass


class UR:

    def __init__(self, type, cbor):
        if not is_ur_type(type):
            raise InvalidType()

        self.type = type
        self.cbor = cbor
        self.cbor_decoder = None
        self.cbor_encoder = None

    def __eq__(self, obj):
        if obj is None:
            return False
        return self.type == obj.type and self.cbor == obj.cbor

    def decode(self):
        self.cbor_decoder = CBORDecoder(self.cbor)

    def encode(self):
        self.cbor_encoder = CBOREncoder()
        self.cbor = self.cbor_encoder.get_bytes()
        return self.cbor


class URBytes(UR):
    """Undifferentiated byte string"""

    def __init__(self, cbor=None, data=None):
        super().__init__('bytes', cbor)
        self.data = data

    def decode(self):
        super().decode()
        self.data, length = self.cbor_decoder.decodeBytes()

    def encode(self):
        super().encode()

        self.cbor_encoder.encodeBytes(self.data)
        self.cbor = self.cbor_encoder.get_bytes()
        return self.cbor


class URCryptoRequest(UR):
    """
    crypto-request uniform resource

    See:
        - https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2021-001-request.md
        - https://github.com/BlockchainCommons/crypto-commons/blob/master/Docs/ur-99-request-response.md
    """

    def __init__(self, cbor=None):
        """
        Initialize UR crypto-request

        Raises an InvalidType exception if type is not crypto-request.
        """

        super().__init__('crypto-request', cbor)

        self.uuid = None

    def decode(self):
        super().decode()

        (size, _) = self.cbor_decoder.decodeMapSize()
        for _ in range(0, size):
            (index, length) = self.cbor_decoder.decodeUnsigned()
            (tag, length) = self.cbor_decoder.decodeTagSemantic()
            # decode
            if tag == _TAG_UUID:
                self._decode_uuid()
            else:
                self._decode_tag(tag)

    def _decode_uuid(self):
        (self.uuid, length) = self.cbor_decoder.decodeBytes()
        if len(self.uuid) != _UUID_LEN:
            raise InvalidUuid()

    def _decode_tag(self, tag):
        """Decode a tag from a crypto-request map"""
        pass


class URCryptoResponse(UR):
    """crypto-response uniform resource"""

    def __init__(self, cbor=None, uuid=None):
        super().__init__('crypto-response', cbor)

        self.uuid = uuid
        self.encode_map_size = 1

    def encode(self):
        super().encode()

        self.cbor_encoder.encodeMapSize(self.encode_map_size)

        self.cbor_encoder.encodeUnsigned(1)
        self.cbor_encoder.encodeTagSemantic(_TAG_UUID)
        self.cbor_encoder.encodeBytes(self.uuid)

        self.cbor = self.cbor_encoder.get_bytes()
        return self.cbor


class EnvoyURCryptoRequest(URCryptoRequest):
    """Envoy crypto-request uniform resource"""

    _TAG_SCV_CHALLENGE_REQUEST = const(710)
    _TAG_PASSPORT_MODEL_REQUEST = const(720)
    _TAG_PASSPORT_FIRMWARE_VERSION_REQUEST = const(770)

    def __init__(self, cbor=None):
        super().__init__(cbor=cbor)

        self.scv_challenge = None
        self.passport_firmware_version_request = False
        self.passport_model_request = False

    def _decode_tag(self, tag):
        if tag == _TAG_SCV_CHALLENGE_REQUEST:
            self._decode_scv_challenge()
        elif tag == _TAG_PASSPORT_MODEL_REQUEST:
            self._decode_passport_model_request()
        elif tag == _TAG_PASSPORT_FIRMWARE_VERSION_REQUEST:
            self._decode_passport_firmware_version_request()

    def _decode_scv_challenge(self):
        self.scv_challenge = {}
        (size, _) = self.cbor_decoder.decodeMapSize()
        if size != 3:
            raise InvalidScvChallenge()

        for _ in range(0, size):
            (index, _) = self.cbor_decoder.decodeUnsigned()
            (text, _) = self.cbor_decoder.decodeText()
            if index == 1:
                self.scv_challenge['id'] = text
            elif index == 2:
                self.scv_challenge['signature'] = text

    def _decode_passport_model_request(self):
        pass

    def _decode_passport_firmware_version_request(self):
        # A dummy unsigned(0) is present.
        self.cbor_decoder.decodeUnsigned()


class EnvoyURCryptoResponse(URCryptoResponse):
    """Envoy crypto-response uniform resource"""

    _TAG_SCV_CHALLENGE_RESPONSE = const(711)
    _TAG_PASSPORT_MODEL_RESPONSE = const(721)
    _TAG_PASSPORT_FIRMWARE_VERSION_RESPONSE = const(771)

    PASSPORT_MODEL_FOUNDERS_EDITION = 1
    PASSPORT_MODEL_BATCH2 = 2

    def __init__(self, uuid=None, words=None, model=PASSPORT_MODEL_BATCH2, version=None):
        super().__init__(uuid=uuid)

        self.words = words
        self.encode_map_size = 4
        self.model = model
        self.version = version

    def encode(self):
        super().encode()

        self.cbor_encoder.encodeUnsigned(2)
        self.cbor_encoder.encodeTagSemantic(_TAG_SCV_CHALLENGE_RESPONSE)

        self.cbor_encoder.encodeMapSize(4)

        self.cbor_encoder.encodeUnsigned(1)
        self.cbor_encoder.encodeText(self.words[0])

        self.cbor_encoder.encodeUnsigned(2)
        self.cbor_encoder.encodeText(self.words[1])

        self.cbor_encoder.encodeUnsigned(3)
        self.cbor_encoder.encodeText(self.words[2])

        self.cbor_encoder.encodeUnsigned(4)
        self.cbor_encoder.encodeText(self.words[3])

        self.cbor_encoder.encodeUnsigned(3)
        self.cbor_encoder.encodeTagSemantic(_TAG_PASSPORT_MODEL_RESPONSE)
        self.cbor_encoder.encodeUnsigned(self.model)

        self.cbor_encoder.encodeUnsigned(4)
        self.cbor_encoder.encodeTagSemantic(_TAG_PASSPORT_FIRMWARE_VERSION_RESPONSE)
        self.cbor_encoder.encodeText(self.version)

        self.cbor = self.cbor_encoder.get_bytes()
        return self.cbor
