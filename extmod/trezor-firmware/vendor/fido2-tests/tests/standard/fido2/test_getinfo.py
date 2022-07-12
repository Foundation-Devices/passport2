import sys
import pytest
from fido2 import cbor
from fido2.ctap import CtapError

from tests.utils import *
from tests.standard.fido2 import TestCborKeysSorted


def test_get_info(info):
    pass


def test_get_info_version(info):
    assert "FIDO_2_0" in info.versions


def test_Check_pin_protocols_field(info):
    if len(info.pin_protocols):
        assert sum(info.pin_protocols) > 0


def test_Check_options_field(info):
    for x in info.options:
        assert info.options[x] in [True, False]


@pytest.mark.skipif('trezor' in sys.argv, reason="User verification flag is intentionally set to true on Trezor even when user verification is not configured. (Otherwise some services refuse registration without giving a reason.)")
def test_Check_uv_option(device, info):
    if "uv" in info.options:
        if info.options["uv"]:
            device.sendMC(*FidoRequest().toMC(), options={"uv": True})


def test_Check_up_option(device, info):
    if "up" in info.options:
        if info.options["up"]:
            with pytest.raises(CtapError) as e:
                device.sendMC(*FidoRequest(options={"up": True}).toMC())
            assert e.value.code == CtapError.ERR.INVALID_OPTION

def test_self_cbor_sorting():
    cbor_key_list_sorted = [
        0,
        1,
        1,
        2,
        3,
        -1,
        -2,
        "b",
        "c",
        "aa",
        "aaa",
        "aab",
        "baa",
        "bbb",
    ]
    TestCborKeysSorted(cbor_key_list_sorted)

def test_self_cbor_integers():
    with pytest.raises(ValueError) as e:
        TestCborKeysSorted([1, 0])

def test_self_cbor_major_type():
    with pytest.raises(ValueError) as e:
        TestCborKeysSorted([-1, 0])

def test_self_cbor_strings():
    with pytest.raises(ValueError) as e:
        TestCborKeysSorted(["bb", "a"])

def test_self_cbor_same_length_strings():
    with pytest.raises(ValueError) as e:
        TestCborKeysSorted(["ab", "aa"])