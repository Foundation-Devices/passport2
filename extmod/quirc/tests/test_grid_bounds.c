// SPDX-FileCopyrightText: Copyright (C) 2026 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "quirc_internal.h"

#define CANARY_SIZE 16
#define CANARY_BYTE 0xa5

struct guarded_code {
	uint8_t before[CANARY_SIZE];
	struct quirc_code code;
	uint8_t after[CANARY_SIZE];
};

static void assert_canaries(const struct guarded_code *guarded)
{
	int i;

	for (i = 0; i < CANARY_SIZE; i++) {
		assert(guarded->before[i] == CANARY_BYTE);
		assert(guarded->after[i] == CANARY_BYTE);
	}
}

static void test_extract_rejects_index_at_count(void)
{
	struct quirc q;
	struct guarded_code guarded;

	memset(&q, 0, sizeof(q));
	memset(&guarded, CANARY_BYTE, sizeof(guarded));
	q.num_grids = 1;
	q.grids[1].grid_size = 21;

	quirc_extract(&q, 1, &guarded.code);

	assert(guarded.code.size == 0);
	assert_canaries(&guarded);
}

static void test_extract_rejects_oversized_grid(void)
{
	struct quirc q;
	struct guarded_code guarded;
	quirc_pixel_t pixel = QUIRC_PIXEL_BLACK;

	memset(&q, 0, sizeof(q));
	memset(&guarded, CANARY_BYTE, sizeof(guarded));

	q.pixels = &pixel;
	q.w = 1;
	q.h = 1;
	q.num_grids = 1;
	q.grids[0].grid_size = QUIRC_MAX_GRID_SIZE + 4;

	quirc_extract(&q, 0, &guarded.code);

	assert(guarded.code.size == QUIRC_MAX_GRID_SIZE + 4);
	assert_canaries(&guarded);
}

static void test_extract_accepts_maximum_grid(void)
{
	struct quirc q;
	struct guarded_code guarded;
	quirc_pixel_t pixel = QUIRC_PIXEL_BLACK;

	memset(&q, 0, sizeof(q));
	memset(&guarded, CANARY_BYTE, sizeof(guarded));

	q.pixels = &pixel;
	q.w = 1;
	q.h = 1;
	q.num_grids = 1;
	q.grids[0].grid_size = QUIRC_MAX_GRID_SIZE;

	quirc_extract(&q, 0, &guarded.code);

	assert(guarded.code.size == QUIRC_MAX_GRID_SIZE);
	assert(guarded.code.cell_bitmap[QUIRC_MAX_BITMAP - 1] == 1);
	assert_canaries(&guarded);
}

static void test_decode_rejects_oversized_grid(void)
{
	struct quirc_code code;
	struct quirc_data data;

	memset(&code, 0, sizeof(code));
	code.size = QUIRC_MAX_GRID_SIZE + 4;

	assert(quirc_decode(&code, &data) == QUIRC_ERROR_INVALID_GRID_SIZE);
}

static void test_decode_accepts_maximum_grid_size(void)
{
	struct quirc_code code;
	struct quirc_data data;

	memset(&code, 0, sizeof(code));
	code.size = QUIRC_MAX_GRID_SIZE;

	assert(quirc_decode(&code, &data) != QUIRC_ERROR_INVALID_GRID_SIZE);
}

int main(void)
{
	test_extract_rejects_index_at_count();
	test_extract_rejects_oversized_grid();
	test_extract_accepts_maximum_grid();
	test_decode_rejects_oversized_grid();
	test_decode_accepts_maximum_grid_size();

	return 0;
}
