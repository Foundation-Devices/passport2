# Select the variant to build for.
VARIANT ?= standard

# If the build directory is not given, make it reflect the variant name.
BUILD ?= build-$(VARIANT)

VARIANT_DIR ?= variants/$(VARIANT)
ifeq ($(wildcard $(VARIANT_DIR)/.),)
$(error Invalid VARIANT specified: $(VARIANT_DIR))
endif

include ../../py/mkenv.mk
-include mpconfigport.mk
include $(VARIANT_DIR)/mpconfigvariant.mk

# use FROZEN_MANIFEST for new projects, others are legacy
FROZEN_MANIFEST ?= variants/manifest.py
FROZEN_DIR =
FROZEN_MPY_DIR =

# This should be configured by the mpconfigvariant.mk
PROG ?= micropython

# qstr definitions (must come before including py.mk)
QSTR_DEFS = qstrdefsport.h
QSTR_GLOBAL_DEPENDENCIES = $(VARIANT_DIR)/mpconfigvariant.h

# OS name, for simple autoconfig
UNAME_S := $(shell uname -s)

# include py core make definitions
include $(TOP)/py/py.mk

GIT_SUBMODULES += lib/axtls lib/berkeley-db-1.xx lib/libffi

INC +=  -I.
INC +=  -I$(TOP)
INC += -I$(BUILD)

# compiler settings
CWARN = -Wall -Werror
CWARN += -Wextra -Wno-unused-parameter -Wpointer-arith -Wdouble-promotion -Wfloat-conversion
CFLAGS += $(INC) $(CWARN) -std=gnu99 -DUNIX $(CFLAGS_MOD) $(COPT) -I$(VARIANT_DIR) $(CFLAGS_EXTRA) $(SIM_CFLAGS)

# Debugging/Optimization
ifdef DEBUG
CFLAGS += -g3
COPT ?= -O0
else
COPT ?= -Os
COPT += -DNDEBUG
endif

# Remove unused sections.
COPT += -fdata-sections -ffunction-sections

# Always enable symbols -- They're occasionally useful, and don't make it into the
# final .bin/.hex/.dfu so the extra size doesn't matter.
CFLAGS += -g

ifndef DEBUG
# _FORTIFY_SOURCE is a feature in gcc/glibc which is intended to provide extra
# security for detecting buffer overflows. Some distros (Ubuntu at the very least)
# have it enabled by default.
#
# gcc already optimizes some printf calls to call puts and/or putchar. When
# _FORTIFY_SOURCE is enabled and compiling with -O1 or greater, then some
# printf calls will also be optimized to call __printf_chk (in glibc). Any
# printfs which get redirected to __printf_chk are then no longer synchronized
# with printfs that go through mp_printf.
#
# In MicroPython, we don't want to use the runtime library's printf but rather
# go through mp_printf, so that stdout is properly tied into streams, etc.
# This means that we either need to turn off _FORTIFY_SOURCE or provide our
# own implementation of __printf_chk. We've chosen to turn off _FORTIFY_SOURCE.
# It should also be noted that the use of printf in MicroPython is typically
# quite limited anyways (primarily for debug and some error reporting, etc
# in the unix version).
#
# Information about _FORTIFY_SOURCE seems to be rather scarce. The best I could
# find was this: https://securityblog.redhat.com/2014/03/26/fortify-and-you/
# Original patchset was introduced by
# https://gcc.gnu.org/ml/gcc-patches/2004-09/msg02055.html .
#
# Turning off _FORTIFY_SOURCE is only required when compiling with -O1 or greater
CFLAGS += -U _FORTIFY_SOURCE
endif

# On OSX, 'gcc' is a symlink to clang unless a real gcc is installed.
# The unix port of MicroPython on OSX must be compiled with clang,
# while cross-compile ports require gcc, so we test here for OSX and
# if necessary override the value of 'CC' set in py/mkenv.mk
ifeq ($(UNAME_S),Darwin)
ifeq ($(MICROPY_FORCE_32BIT),1)
CC = clang -m32
else
CC = clang
endif
# Use clang syntax for map file
LDFLAGS_ARCH = -Wl,-map,$@.map -Wl,-dead_strip
else
# Use gcc syntax for map file
LDFLAGS_ARCH = -Wl,-Map=$@.map,--cref -Wl,--gc-sections
endif
LDFLAGS += $(LDFLAGS_MOD) $(LDFLAGS_ARCH) -lm $(LDFLAGS_EXTRA)

# Flags to link with pthread library
LIBPTHREAD = -lpthread

ifeq ($(MICROPY_FORCE_32BIT),1)
# Note: you may need to install i386 versions of dependency packages,
# starting with linux-libc-dev:i386
ifeq ($(MICROPY_PY_FFI),1)
ifeq ($(UNAME_S),Linux)
CFLAGS_MOD += -I/usr/include/i686-linux-gnu
endif
endif
endif

ifeq ($(MICROPY_USE_READLINE),1)
INC +=  -I$(TOP)/lib/mp-readline
CFLAGS_MOD += -DMICROPY_USE_READLINE=1
LIB_SRC_C_EXTRA += mp-readline/readline.c
endif
ifeq ($(MICROPY_PY_TERMIOS),1)
CFLAGS_MOD += -DMICROPY_PY_TERMIOS=1
SRC_MOD += modtermios.c
endif
ifeq ($(MICROPY_PY_SOCKET),1)
CFLAGS_MOD += -DMICROPY_PY_SOCKET=1
SRC_MOD += modusocket.c
endif
ifeq ($(MICROPY_PY_THREAD),1)
CFLAGS_MOD += -DMICROPY_PY_THREAD=1 -DMICROPY_PY_THREAD_GIL=0
LDFLAGS_MOD += $(LIBPTHREAD)
endif

# If the variant enables it, enable modbluetooth.
ifeq ($(MICROPY_PY_BLUETOOTH),1)

HAVE_LIBUSB := $(shell (which pkg-config > /dev/null && pkg-config --exists libusb-1.0) 2>/dev/null && echo '1')

# Only one stack can be enabled.
ifeq ($(MICROPY_BLUETOOTH_NIMBLE),1)
ifeq ($(MICROPY_BLUETOOTH_BTSTACK),1)
$(error Cannot enable both NimBLE and BTstack at the same time)
endif
endif

# Default to btstack, but a variant (or make command line) can set NimBLE
# explicitly (which is always via H4 UART).
ifneq ($(MICROPY_BLUETOOTH_NIMBLE),1)
ifneq ($(MICROPY_BLUETOOTH_BTSTACK),1)
MICROPY_BLUETOOTH_BTSTACK ?= 1
endif
endif

CFLAGS_MOD += -DMICROPY_PY_BLUETOOTH=1
CFLAGS_MOD += -DMICROPY_PY_BLUETOOTH_ENABLE_CENTRAL_MODE=1

ifeq ($(MICROPY_BLUETOOTH_BTSTACK),1)

# Figure out which BTstack transport to use.
ifeq ($(MICROPY_BLUETOOTH_BTSTACK_H4),1)
ifeq ($(MICROPY_BLUETOOTH_BTSTACK_USB),1)
$(error Cannot enable BTstack support for USB and H4 UART at the same time)
endif
else
ifeq ($(HAVE_LIBUSB),1)
# Default to btstack-over-usb.
MICROPY_BLUETOOTH_BTSTACK_USB ?= 1
else
# Fallback to HCI controller via a H4 UART (e.g. Zephyr on nRF) over a /dev/tty serial port.
MICROPY_BLUETOOTH_BTSTACK_H4 ?= 1
endif
endif

# BTstack is enabled.
GIT_SUBMODULES += lib/btstack
include $(TOP)/extmod/btstack/btstack.mk
SRC_BTSTACK += lib/btstack/platform/embedded/btstack_run_loop_embedded.c

else

# NimBLE is enabled.
GIT_SUBMODULES += lib/mynewt-nimble
CFLAGS_MOD += -DMICROPY_PY_BLUETOOTH_ENABLE_L2CAP_CHANNELS=1
include $(TOP)/extmod/nimble/nimble.mk

endif

endif

ifeq ($(MICROPY_PY_FFI),1)

ifeq ($(MICROPY_STANDALONE),1)
LIBFFI_CFLAGS_MOD := -I$(shell ls -1d $(BUILD)/lib/libffi/out/lib/libffi-*/include)
 ifeq ($(MICROPY_FORCE_32BIT),1)
  LIBFFI_LDFLAGS_MOD = $(BUILD)/lib/libffi/out/lib32/libffi.a
 else
  LIBFFI_LDFLAGS_MOD = $(BUILD)/lib/libffi/out/lib/libffi.a
 endif
else
LIBFFI_CFLAGS_MOD := $(shell pkg-config --cflags libffi)
LIBFFI_LDFLAGS_MOD := $(shell pkg-config --libs libffi)
endif

ifeq ($(UNAME_S),Linux)
LIBFFI_LDFLAGS_MOD += -ldl
endif

CFLAGS_MOD += $(LIBFFI_CFLAGS_MOD) -DMICROPY_PY_FFI=1
LDFLAGS_MOD += $(LIBFFI_LDFLAGS_MOD)
SRC_MOD += modffi.c
endif

ifeq ($(MICROPY_PY_JNI),1)
# Path for 64-bit OpenJDK, should be adjusted for other JDKs
CFLAGS_MOD += -I/usr/lib/jvm/java-7-openjdk-amd64/include -DMICROPY_PY_JNI=1
SRC_MOD += modjni.c
endif

# source files
SRC_C += \
	main.c \
	gccollect.c \
	unix_mphal.c \
	mpthreadport.c \
	input.c \
	modmachine.c \
	modos.c \
	moduos_vfs.c \
	modtime.c \
	moduselect.c \
	alloc.c \
	fatfs_port.c \
	mpbthciport.c \
	mpbtstackport_common.c \
	mpbtstackport_h4.c \
	mpbtstackport_usb.c \
	mpnimbleport.c \
	modpassport_lv.c \
	ring_buffer.c \
	$(SRC_MOD) \
	$(wildcard $(VARIANT_DIR)/*.c)

LIB_SRC_C += $(addprefix lib/,\
	$(LIB_SRC_C_EXTRA) \
	timeutils/timeutils.c \
	utils/gchelper_generic.c \
	)

ifneq ($(UNAME_S),Darwin)
LIB_SRC_C += $(addprefix lib/,\
	lv_bindings/driver/linux/modfb.c \
	)
endif

SRC_CXX += \
	$(SRC_MOD_CXX)

OBJ = $(PY_O)
OBJ += $(addprefix $(BUILD)/, $(SRC_C:.c=.o))
OBJ += $(addprefix $(BUILD)/, $(SRC_CXX:.cpp=.o))
OBJ += $(addprefix $(BUILD)/, $(LIB_SRC_C:.c=.o))
OBJ += $(addprefix $(BUILD)/, $(EXTMOD_SRC_C:.c=.o))

# List of sources for qstr extraction
SRC_QSTR += $(SRC_C) $(SRC_CXX) $(LIB_SRC_C) $(EXTMOD_SRC_C)
# Append any auto-generated sources that are needed by sources listed in
# SRC_QSTR
SRC_QSTR_AUTO_DEPS +=

ifneq ($(FROZEN_MANIFEST)$(FROZEN_MPY_DIR),)
# To use frozen code create a manifest.py file with a description of files to
# freeze, then invoke make with FROZEN_MANIFEST=manifest.py (be sure to build from scratch).
CFLAGS += -DMICROPY_QSTR_EXTRA_POOL=mp_qstr_frozen_const_pool
CFLAGS += -DMICROPY_MODULE_FROZEN_MPY
CFLAGS += -DMPZ_DIG_SIZE=16 # force 16 bits to work on both 32 and 64 bit archs
MPY_CROSS_FLAGS += -mcache-lookup-bc
endif

ifneq ($(FROZEN_MANIFEST)$(FROZEN_DIR),)
CFLAGS += -DMICROPY_MODULE_FROZEN_STR
endif

HASCPP17 = $(shell expr `$(CC) -dumpversion | cut -f1 -d.` \>= 7)
ifeq ($(HASCPP17), 1)
	CXXFLAGS += -std=c++17
else
	CXXFLAGS += -std=c++11
endif
CXXFLAGS += $(filter-out -Wmissing-prototypes -Wold-style-definition -std=gnu99,$(CFLAGS) $(CXXFLAGS_MOD))

ifeq ($(MICROPY_FORCE_32BIT),1)
RUN_TESTS_MPY_CROSS_FLAGS = --mpy-cross-flags='-mcache-lookup-bc -march=x86'
else
RUN_TESTS_MPY_CROSS_FLAGS = --mpy-cross-flags='-mcache-lookup-bc'
endif

include $(TOP)/py/mkrules.mk

.PHONY: test test_full

test: $(PROG) $(TOP)/tests/run-tests.py
	$(eval DIRNAME=ports/$(notdir $(CURDIR)))
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py

test_full: $(PROG) $(TOP)/tests/run-tests.py
	$(eval DIRNAME=ports/$(notdir $(CURDIR)))
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py -d thread
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py --emit native
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py --via-mpy $(RUN_TESTS_MPY_CROSS_FLAGS) -d basics float micropython
	cd $(TOP)/tests && MICROPY_MICROPYTHON=../$(DIRNAME)/$(PROG) ./run-tests.py --via-mpy $(RUN_TESTS_MPY_CROSS_FLAGS) --emit native -d basics float micropython
	cat $(TOP)/tests/basics/0prelim.py | ./$(PROG) | grep -q 'abc'

test_gcov: test_full
	gcov -o $(BUILD)/py $(TOP)/py/*.c
	gcov -o $(BUILD)/extmod $(TOP)/extmod/*.c

# Value of configure's --host= option (required for cross-compilation).
# Deduce it from CROSS_COMPILE by default, but can be overridden.
ifneq ($(CROSS_COMPILE),)
CROSS_COMPILE_HOST = --host=$(patsubst %-,%,$(CROSS_COMPILE))
else
CROSS_COMPILE_HOST =
endif

deplibs: libffi axtls

libffi: $(BUILD)/lib/libffi/include/ffi.h

$(TOP)/lib/libffi/configure: $(TOP)/lib/libffi/autogen.sh
	cd $(TOP)/lib/libffi; ./autogen.sh

# install-exec-recursive & install-data-am targets are used to avoid building
# docs and depending on makeinfo
$(BUILD)/lib/libffi/include/ffi.h: $(TOP)/lib/libffi/configure
	mkdir -p $(BUILD)/lib/libffi; cd $(BUILD)/lib/libffi; \
	$(abspath $(TOP))/lib/libffi/configure $(CROSS_COMPILE_HOST) --prefix=$$PWD/out --disable-structs CC="$(CC)" CXX="$(CXX)" LD="$(LD)" CFLAGS="-Os -fomit-frame-pointer -fstrict-aliasing -ffast-math -fno-exceptions"; \
	$(MAKE) install-exec-recursive; $(MAKE) -C include install-data-am

axtls: $(TOP)/lib/axtls/README

$(TOP)/lib/axtls/README:
	@echo "You cloned without --recursive, fetching submodules for you."
	(cd $(TOP); git submodule update --init --recursive)

PREFIX = /usr/local
BINDIR = $(DESTDIR)$(PREFIX)/bin

install: $(PROG)
	install -d $(BINDIR)
	install $(PROG) $(BINDIR)/$(PROG)

uninstall:
	-rm $(BINDIR)/$(PROG)
