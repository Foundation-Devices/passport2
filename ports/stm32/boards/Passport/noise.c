// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <string.h>

#ifndef FACTORY_TEST
#include <assert.h>
#endif

#include "noise.h"
#include "adc.h"
#include "pprng.h"
#include "utils.h"
#include "se.h"

#ifndef FACTORY_TEST
#include "frequency.h"
#endif

#include "stm32h7xx_hal.h"

static unsigned int _users = 0;

void noise_enable() {
    adc_enable_noise();
    _users++;
}

void noise_disable() {
    if (_users > 0) {
        _users--;
    }

    if (_users == 0) {
        adc_disable_noise();
    }
}

bool noise_get_random_uint16(uint16_t* result) {
    int      ret;
    uint32_t noise1 = 0;
    uint32_t noise2 = 0;
    uint16_t r      = 0;

    for (int i = 0; i < 4; i++) {
        r = r << 4;

        HAL_Delay(1);

        ret = adc_read_noise_inputs(&noise1, &noise2);
        if (ret < 0) {
            return false;
        }

        r ^= noise1 ^ noise2;
    }
    *result = r;
    return true;
}

bool noise_get_random_bytes(uint8_t sources, void* buf, size_t buf_len) {
    // Buffer must be at least 4 bytes - if less is needed, caller can extract 1-3 bytes from a 4-byte buffer.
    // Reject undersized buffers before enabling the turbo clock.
    if (buf_len < 4) {
        return false;
    }

// Need to be fast for this
#ifndef FACTORY_TEST
    frequency_turbo(true);
#endif

    // printf("sources = 0x%02x  buf_len=%d\n", sources, buf_len);
    if (!(sources & NOISE_AVALANCHE_SOURCE) && !(sources & NOISE_MCU_RNG_SOURCE) && !(sources & NOISE_SE_RNG_SOURCE)) {
        // printf("Bad sources, so picking Avalanche!\n");
        // Ensure we always use at least one high entropy source even if caller made a mistake.
        // If you just want als value, you can read it separately.
        sources |= NOISE_AVALANCHE_SOURCE;
    }

    if (sources & NOISE_AVALANCHE_SOURCE) {
        uint8_t* pbuf8 = (uint8_t*)buf;
        for (int i = 0; i < buf_len;) {
            uint8_t sample[2];
            bool    result = noise_get_random_uint16((uint16_t*)sample);
            if (!result) {
#ifndef FACTORY_TEST
                frequency_turbo(false);
#endif
                // printf("failed to get Avalanche sample!\n");
                return false;
            }

            // printf("AVALANCHE SAMPLE: 0x%02x%02x\n", sample[0], sample[1]);
            if (i < buf_len) {
                pbuf8[i] = sample[0];
                i++;
            }
            if (i < buf_len) {
                pbuf8[i] = sample[1];
                i++;
            }
        }
    }

#ifndef FACTORY_TEST
    // MCU RNG
    if (sources & NOISE_MCU_RNG_SOURCE) {
        // printf("Using MCU source\n");
        uint8_t* pbuf8     = (uint8_t*)buf;
        uint8_t* pbuf8_end = pbuf8 + buf_len;

        // Mix MCU entropy into every byte, including any partial final sample.
        while (pbuf8 < pbuf8_end) {
            uint32_t sample = rng_sample();
            // printf("MCU SAMPLE: 0x%08lx\n", sample);

            // XOR in the sample - don't overflow output buffer
            int len = (int)MIN((size_t)(pbuf8_end - pbuf8), sizeof(sample));
            xor_mixin(pbuf8, (uint8_t*)&sample, len);
            pbuf8 += len;
        }
    }

    // Secure Element RNG
    if (sources & NOISE_SE_RNG_SOURCE) {
        uint8_t* pbuf8     = (uint8_t*)buf;
        uint8_t* pbuf8_end = pbuf8 + buf_len;
        uint8_t  num_in[20], sample[32];
        memset(num_in, 0, 20);

        // Mix secure element entropy into every byte, including any partial final sample.
        while (pbuf8 < pbuf8_end) {
            int rc = se_pick_nonce(num_in, sample);
            if (rc < 0) {
                se_show_error();
#ifndef FACTORY_TEST
                frequency_turbo(false);
#endif
                return false;
            }

            // uint32_t* s = (uint32_t*)sample;
            // printf("SE SAMPLE: 0x%08lx %08lx %08lx %08lx\n", *s, *(s+1), *(s+2), *(s+3));

            // Mixin the sample values - don't overflow output buffer
            int len = (int)MIN((size_t)(pbuf8_end - pbuf8), sizeof(sample));
            xor_mixin(pbuf8, sample, len);
            pbuf8 += len;
        }
    }

    // printf("1 buf: ");
    // uint8_t* pbuf8 = (uint8_t*)buf_info.buf;
    // for (int i=0; i<buf_info.len; i++) {
    //    printf("%02x", pbuf8[i]);
    // }
    // printf("\n");

    // print_hex_buf("Final buf: ", buf_info.buf, buf_info.len);
    frequency_turbo(false);
#endif

    return true;
}

// trezor-firmware randomness functions
//
// These back trezor-crypto's internal randomness, where an avalanche sample per
// call would be paid on every operation. Their consumers are blinding and nonce
// material in ecdsa.c and zkp_context.c, and trezorcrypto.random, which
// ext_settings.py uses for wear levelling and deniability padding.
//
// Secret generation is not one of them - see new_seed_task, which asks
// noise_get_random_bytes() for every source.

void random_reseed(const uint32_t value) {
    (void)value;
}

uint32_t random32(void) {
    bool     ret;
    uint32_t tmp = 0;
    (void)ret;
    noise_enable();
    ret = noise_get_random_bytes(NOISE_MCU_RNG_SOURCE, &tmp, sizeof(tmp));
    noise_disable();
#ifndef FACTORY_TEST
    assert(ret);
#endif
    return tmp;
}

void random_buffer(uint8_t* buf, size_t len) {
    uint32_t tmp;
    bool     ret;
    (void)ret;

    // noise_get_random_bytes requirest at least 4 bytes.
    if (len < 4) {
        tmp = random32();
        memcpy(buf, &tmp, len);
        return;
    }

    noise_enable();
    ret = noise_get_random_bytes(NOISE_MCU_RNG_SOURCE, buf, len);
    noise_disable();
#ifndef FACTORY_TEST
    assert(ret);
#endif
}
