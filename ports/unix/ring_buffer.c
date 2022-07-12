// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
#include <stdio.h>

#include "ring_buffer.h"

static ring_buffer_t keybuf;

/**
 * Code adapted from https://github.com/AndersKaloer/Ring-Buffer
 */

int ring_buffer_init(void) {
    keybuf.size       = MAX_RING_BUFFER_SIZE;
    keybuf.size_plus1 = MAX_RING_BUFFER_SIZE + 1;
    keybuf.head_index = 0;
    keybuf.tail_index = 0;
    return 0;
}

void ring_buffer_enqueue(uint8_t data) {
    if (ring_buffer_is_full()) {
        keybuf.tail_index = ((keybuf.tail_index + 1) % keybuf.size_plus1);
    }

    keybuf.buffer[keybuf.head_index] = data;
    keybuf.head_index                = ((keybuf.head_index + 1) % keybuf.size_plus1);
}

uint8_t ring_buffer_dequeue(uint8_t* data) {
    if (ring_buffer_is_empty()) {
        return 0;
    }

    *data             = keybuf.buffer[keybuf.tail_index];
    keybuf.tail_index = ((keybuf.tail_index + 1) % keybuf.size_plus1);
    return 1;
}

uint8_t ring_buffer_peek(uint8_t* data, ring_buffer_size_t index) {
    if (index >= ring_buffer_num_items()) {
        return 0;
    }

    ring_buffer_size_t data_index = ((keybuf.tail_index + index) % keybuf.size_plus1);
    *data                         = keybuf.buffer[data_index];
    return 1;
}

uint8_t ring_buffer_is_empty(void) {
    uint8_t result = (keybuf.head_index == keybuf.tail_index);
    return result;
}

uint8_t ring_buffer_is_full(void) {
    uint8_t num_items = ring_buffer_num_items();
    uint8_t result    = num_items == keybuf.size;
    return result;
}

ring_buffer_size_t ring_buffer_num_items(void) {
    uint8_t result = (keybuf.head_index + keybuf.size_plus1 - keybuf.tail_index) % keybuf.size_plus1;
    return result;
}
