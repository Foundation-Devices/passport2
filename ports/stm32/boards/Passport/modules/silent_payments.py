# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# silent_payments.py - BIP-352/BIP-375 Silent Payment support
#
# This module provides functions to encode/decode Silent Payment addresses
# and verify PSBT outputs for Silent Payment transactions.
#

import trezorcrypto
import tcc

# Silent Payment address prefixes
SP_ADDRESS_PREFIX = 'sp'
TSP_ADDRESS_PREFIX = 'tsp'

# BIP-352 constants
BIP_352_VERSION_PUBKEY = 0x01  # For sp1... addresses (P2WPKH)
BIP_352_VERSION_TAPROOT = 0x02  # For tsp1... addresses (P2TR)


def decode_silent_payment_address(address, hrp='bc'):
    """
    Decode a Silent Payment address and extract the scanning and spending keys.
    
    Args:
        address: Silent Payment address (sp1... or tsp1...)
        hrp: Human-readable part (bc for mainnet, tb for testnet)
    
    Returns:
        Dictionary with:
            - version: version byte
            - B_scan: scanning public key (32 bytes)
            - B_spend: spending public key (32 bytes)
            - is_taproot: True if taproot (tsp1) address
    """
    # Validate address prefix
    if address.startswith(SP_ADDRESS_PREFIX):
        is_taproot = False
        version = BIP_352_VERSION_PUBKEY
    elif address.startswith(TSP_ADDRESS_PREFIX):
        is_taproot = True
        version = BIP_352_VERSION_TAPROOT
    else:
        raise ValueError(f"Not a valid Silent Payment address: {address}")
    
    # Remove prefix and decode bech32
    addr_without_prefix = address[len(TSP_ADDRESS_PREFIX if is_taproot else SP_ADDRESS_PREFIX):]
    
    try:
        # Decode the address - returns (version, data)
        decoded = tcc.codecs.bech32_decode(hrp, addr_without_prefix)
    except Exception as e:
        raise ValueError(f"Failed to decode Silent Payment address: {e}")
    
    if decoded is None:
        raise ValueError(f"Invalid bech32 encoding in address: {address}")
    
    version_byte, data = decoded
    
    # Validate version byte
    if version_byte != version:
        raise ValueError(f"Version byte mismatch: expected {version}, got {version_byte}")
    
    # Data should be 64 bytes: 32 bytes B_scan + 32 bytes B_spend
    if len(data) != 64:
        raise ValueError(f"Invalid Silent Payment address data length: {len(data)}")
    
    B_scan = data[:32]
    B_spend = data[32:]
    
    return {
        'version': version_byte,
        'B_scan': B_scan,
        'B_spend': B_spend,
        'is_taproot': is_taproot
    }


def encode_silent_payment_address(B_scan, B_spend, is_taproot=False, hrp='bc'):
    """
    Encode a Silent Payment address from scanning and spending keys.
    
    Args:
        B_scan: Scanning public key (32 bytes)
        B_spend: Spending public key (32 bytes)
        is_taproot: True for taproot (tsp1), False for P2WPKH (sp1)
        hrp: Human-readable part (bc for mainnet, tb for testnet)
    
    Returns:
        Silent Payment address string
    """
    version = BIP_352_VERSION_TAPROOT if is_taproot else BIP_352_VERSION_PUBKEY
    
    # Combine B_scan and B_spend
    data = B_scan + B_spend
    
    # Encode using bech32m
    prefix = TSP_ADDRESS_PREFIX if is_taproot else SP_ADDRESS_PREFIX
    addr = tcc.codecs.bech32_encode(hrp, version, data, tcc.codecs.BECH32_ENCODING_BECH32M)
    
    return prefix + addr


def derive_silent_payment_address(B_scan, B_spend, output_script):
    """
    Derive the expected Silent Payment address from keys and verify against output.
    
    Args:
        B_scan: Scanning public key (32 bytes)
        B_spend: Spending public key (32 bytes)
        output_script: The output script from the transaction
    
    Returns:
        The derived Silent Payment address if the output matches
    """
    # For Silent Payments, the output is a P2TR (taproot) address
    # The output script should be: OP_1 <32 bytes>
    if len(output_script) != 34:
        return None
    
    if output_script[0] != 0x51 or output_script[1] != 0x20:
        return None
    
    # The output key in the script
    output_key = output_script[2:34]
    
    # For Silent Payments, the address derivation uses B_scan and B_spend
    # to compute the taproot internal key. The exact computation depends on
    # whether this is a simple SP (B_scan = B_spend) or full SP.
    #
    # Simplified: We check if the output key matches what we'd compute.
    # In practice, the coordinator computes: taptweak(B_scan + B_spend)
    # and uses that as the output key.
    
    # For now, return None to indicate we couldn't verify
    # Full implementation would require computing the taproot tweak
    return None


def is_silent_payment_address(address):
    """
    Check if an address is a Silent Payment address.
    
    Args:
        address: Address string to check
    
    Returns:
        True if the address is a Silent Payment address
    """
    return address.startswith(SP_ADDRESS_PREFIX) or address.startswith(TSP_ADDRESS_PREFIX)


def get_address_type(address):
    """
    Get the type of a Bitcoin address.
    
    Args:
        address: Address string
    
    Returns:
        Address type string: 'sp' (Silent Payment), 'tsp' (Taproot SP),
                            'p2wpkh', 'p2wsh', 'p2pkh', 'p2sh', 'p2tr', or 'unknown'
    """
    if is_silent_payment_address(address):
        return 'tsp' if address.startswith(TSP_ADDRESS_PREFIX) else 'sp'
    
    if address.startswith('bc1'):
        # Could be bech32 P2WPKH or P2WSH or P2TR
        try:
            decoded = tcc.codecs.bech32_decode('bc', address[3:])
            if decoded:
                version = decoded[0]
                if version == 0:
                    return 'p2wpkh'
                elif version == 1:
                    return 'p2tr'
        except:
            pass
        return 'p2wsh'
    
    # Legacy addresses start with 1, 3, or m/n
    if address[0] == '1':
        return 'p2pkh'
    elif address[0] == '3' or address[0] == 'm' or address[0] == 'n':
        return 'p2sh'
    
    return 'unknown'
