# SPDX-FileCopyrightText: Copyright (C) 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

QUIRC_DIR := ..
PASSPORT_INCLUDE := ../../../ports/stm32/boards/Passport/include
SOURCES := test_grid_bounds.c \
	$(QUIRC_DIR)/identify.c \
	$(QUIRC_DIR)/decode.c \
	$(QUIRC_DIR)/quirc.c \
	$(QUIRC_DIR)/version_db.c

CFLAGS += -std=c99 -Wall -Wextra -Werror -Wno-unused-parameter
CFLAGS += -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS += -fsanitize=address,undefined -lm

.PHONY: test clean

test: test_grid_bounds
	./test_grid_bounds

test_grid_bounds: $(SOURCES)
	$(CC) $(CFLAGS) -I$(QUIRC_DIR) -I$(PASSPORT_INCLUDE) $^ $(LDFLAGS) -o $@

clean:
	rm -f test_grid_bounds
