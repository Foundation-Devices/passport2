// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "image_conversion.h"

// #define INVERT_IMAGE

// #ifdef SCREEN_MODE_MONO
// void resize_by_nearest_neighbor(uint8_t* grayscale,
//                                 uint32_t gray_hor_res,
//                                 uint32_t gray_ver_res,
//                                 uint16_t y_start,
//                                 uint8_t* mono,
//                                 uint32_t mono_width,
//                                 uint32_t mono_height) {
//     float step = (float)gray_hor_res / (float)mono_width;
//     // printf("gray_hor_res=%lu gray_ver_res=%lu mono_width=%lu mono_height=%lu y_start=%u step=%f\n", gray_hor_res, gray_ver_res, mono_width, mono_height, y_start, step);
//     // float src_y = y_start;
//     // float src_x = 0;
//     uint32_t mono_span = mono_width >> 3;
//
//     // Clear the mono buffer
// #ifdef INVERT_IMAGE
//     memset(mono, 0xFF, (mono_width * mono_height) >> 3);
// #else
//     memset(mono, 0x00, (mono_width * mono_height) >> 3);
// #endif
//
//     for (uint32_t y = 0; y < mono_height; y++) {
//         for (uint32_t x = 0; x < mono_width; x++) {
//             uint32_t offset =
//                 ((uint32_t)((float)(y + y_start) * step) * (uint32_t)gray_hor_res) + (uint32_t)((float)x * step);
//             uint8_t gray = grayscale[offset];
//
//             // if (x < 5) {
//             //     printf("[%02lx]=%02x ", offset, gray);
//             // }
//
//             // Mask the value in it
//             if (gray > 64) {
//                 uint32_t mono_offset = (y * mono_span) + (x >> 3);
//                 uint8_t* p_byte      = &mono[mono_offset];
//
//                 uint8_t bit = x % 8;
// #ifdef INVERT_IMAGE
//                 *p_byte &= ~(1 << (7 - bit));
// #else
//                 *p_byte |= 1 << (7 - bit);
// #endif
//             }
//             // src_x += step;
//         }
//         // printf("\n");
//
//         // src_y += step;
//     }
// }
// #endif

void convert_rgb565_to_grayscale(uint8_t *rgb565,
                                 uint8_t *grayscale,
                                 uint32_t gray_hor_res,
                                 uint32_t gray_ver_res)
{
    // printf("gray_hor_res=%lu gray_ver_res=%lu\n", gray_hor_res, gray_ver_res);
    // printf("rgb565=%08x grayscale=%08x\n", (void*)rgb565, (void*)grayscale);

    for (uint32_t y = 0; y < gray_ver_res; y++) {
        uint32_t line = y * (gray_hor_res * sizeof(uint16_t));
        for (uint32_t x = 0; x < gray_hor_res; x++) {
            uint32_t index = line + (x * sizeof(uint16_t));
#ifdef PASSPORT_SIMULATOR
            /* The passport simulator RGB565 camera data isn't byte-swapped */
            uint16_t pixel = rgb565[index + 1] << 8 | rgb565[index];
#else
            uint16_t pixel = rgb565[index] << 8 | rgb565[index + 1];
#endif

            // Use approximate values for calculating luminance values assuming
            // a ITU-R color space.
            //
            // The values are first converted into RGB888 for the calculation.
            uint32_t r = ((uint32_t)(pixel & 0xF800) >> 11) << 3;
            uint32_t g = ((uint32_t)(pixel & 0x07E0) >> 5) << 2;
            uint32_t b = ((uint32_t)(pixel & 0x001F) >> 0) << 3;
            grayscale[y * gray_hor_res + x] = (uint8_t)(((r * 39) + (g * 150) + (b * 29)) >> 8);
        }
    }
}
