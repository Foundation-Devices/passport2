# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

TOP = ../..

SOURCES  = add-secrets.c

VPATH  = 

ARCH ?= x86

CFLAGS  = -Wall -fno-strict-aliasing
CFLAGS += -fno-omit-frame-pointer
CFLAGS += -I$(TOP)/include

LDFLAGS  = -Wl,-Map,$(MAP)

LIBS  =

CROSS_COMPILE	?= 
CC              = $(CROSS_COMPILE)gcc
EXECUTABLE      = add-secrets
TARGETDIR       = x86

ifeq ($(findstring debug,$(MAKECMDGOALS)),debug)
OBJDIR = $(TARGETDIR)/debug
CFLAGS += -g -DDEBUG
LDFLAGS += -g
STRIP =
else
OBJDIR = $(TARGETDIR)/release
CFLAGS += -O2
STRIP = $(CROSS_COMPILE)strip
endif

PROGRAMDIR	= $(OBJDIR)
INSTALL_DIR	= $(HOME)/bin
PROGRAM		= $(PROGRAMDIR)/$(EXECUTABLE)
MAP		= $(PROGRAMDIR)/$(EXECUTABLE).map

OBJECTS = $(addprefix $(OBJDIR)/,$(SOURCES:.c=.o))

RM := rm -rf

all: $(PROGRAM)

debug: $(PROGRAM)

# Tool invocations
$(PROGRAM): $(OBJECTS) FORCE
	@echo 'Building target: $@'
	@echo 'Invoking: GCC C Linker'
	@[ -d $(dir $@) ] || mkdir -p $(dir $@)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS) $(LIBS)
	@echo 'Finished building target: $@'
	@echo ' '

# Other Targets
clean: FORCE
	@$(RM) $(TARGETDIR)

$(OBJDIR)/%.o:  %.c
	@rm -f $@
	@[ -d $(dir $@) ] || mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -MMD -MP -o $@ $<

ifneq ($(MAKECMDGOALS),clean)
-include $(OBJECTS:.o=.d)
endif

install: $(PROGRAM)
	@echo 'Installing $(PROGRAM)...'
	@cp -f $(PROGRAM) $(INSTALL_DIR)
	@[ -z $(STRIP) ] || $(STRIP) $(INSTALL_DIR)/$(EXECUTABLE)
	@echo 'Installation complete'

.PHONY: all clean install FORCE
.SECONDARY:
