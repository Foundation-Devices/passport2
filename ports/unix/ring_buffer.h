// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef RING_BUFFER_H_
#define RING_BUFFER_H_
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#define MAX_RING_BUFFER_SIZE 16

typedef uint8_t ring_buffer_size_t;

typedef struct _ring_buffer_t {
    // No dynamic allocation
    int                buffer[MAX_RING_BUFFER_SIZE + 1];
    int                size;
    int                size_plus1;
    ring_buffer_size_t tail_index;
    ring_buffer_size_t head_index;
} ring_buffer_t;

/**
 * Initializes or resets the ring buffer.
 * @return 0 if successful; -1 otherwise.
 */
int ring_buffer_init(void);

/**
 * Adds a byte to a ring buffer.
 * @param data The byte to place.
 */
void ring_buffer_enqueue(uint8_t data);

/**
 * Returns the oldest byte in a ring buffer.
 * @param data A pointer to the location at which the data should be placed.
 * @return 1 if data was returned; 0 otherwise.
 */
uint8_t ring_buffer_dequeue(uint8_t* data);

/**
 * Peeks a ring buffer, i.e. returns an element without removing it.
 * @param data A pointer to the location at which the data should be placed.
 * @param index The index to peek.
 * @return 1 if data was returned; 0 otherwise.
 */
uint8_t ring_buffer_peek(uint8_t* data, ring_buffer_size_t index);

/**
 * Returns whether a ring buffer is empty.
 * @return 1 if empty; 0 otherwise.
 */
uint8_t ring_buffer_is_empty(void);

/**
 * Returns whether a ring buffer is full.
 * @return 1 if full; 0 otherwise.
 */
uint8_t ring_buffer_is_full(void);

/**
 * Returns the number of items in a ring buffer.
 * @return The number of items in the ring buffer.
 */
ring_buffer_size_t ring_buffer_num_items(void);

#endif
