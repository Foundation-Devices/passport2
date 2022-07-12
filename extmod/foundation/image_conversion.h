// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdint.h>

// Convert the RGB565 image to 1-byte-per-pixel grayscale
// The conversion is performed with a 90 degree rotation due to the fact that the camera is installed portrait,
// but the data stream is still the landscape orientation.
//
// This function is very much hard-coded to our use case where the grayscale image is used for QR decoding,
// and the monochrome image is cropped and used for the viewfinder image on screen.
void convert_rgb565_to_grayscale(uint8_t *rgb565,
                                 uint8_t *grayscale,
                                 uint32_t gray_hor_res,
                                 uint32_t gray_ver_res);
