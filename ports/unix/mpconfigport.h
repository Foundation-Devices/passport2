/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013, 2014 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

// Options to control how MicroPython is built for this port,
// overriding defaults in py/mpconfig.h.

// Variant-specific definitions.
#include "mpconfigvariant.h"

#define PASSPORT_FOUNDATION_ENABLED (1)
#define MICROPY_PY_TREZORCRYPTO (1)
#define MICROPY_PY_FRAMEBUF         (1)
#define MICROPY_PY_COLLECTIONS      (1)

// The minimal variant's config covers everything.
// If we're building the minimal variant, ignore the rest of this file.
#ifndef MICROPY_UNIX_MINIMAL

#define MICROPY_ALLOC_PATH_MAX      (PATH_MAX)
#define MICROPY_PERSISTENT_CODE_LOAD (1)
#if !defined(MICROPY_EMIT_X64) && defined(__x86_64__)
    #define MICROPY_EMIT_X64        (1)
#endif
#if !defined(MICROPY_EMIT_X86) && defined(__i386__)
    #define MICROPY_EMIT_X86        (1)
#endif
#if !defined(MICROPY_EMIT_THUMB) && defined(__thumb2__)
    #define MICROPY_EMIT_THUMB      (1)
    #define MICROPY_MAKE_POINTER_CALLABLE(p) ((void *)((mp_uint_t)(p) | 1))
#endif
// Some compilers define __thumb2__ and __arm__ at the same time, let
// autodetected thumb2 emitter have priority.
#if !defined(MICROPY_EMIT_ARM) && defined(__arm__) && !defined(__thumb2__)
    #define MICROPY_EMIT_ARM        (1)
#endif
#define MICROPY_COMP_MODULE_CONST   (1)
#define MICROPY_COMP_TRIPLE_TUPLE_ASSIGN (1)
#define MICROPY_COMP_RETURN_IF_EXPR (1)
#define MICROPY_ENABLE_GC           (1)
#define MICROPY_ENABLE_FINALISER    (1)
#define MICROPY_STACK_CHECK         (1)
#define MICROPY_MALLOC_USES_ALLOCATED_SIZE (0)
#define MICROPY_MEM_STATS           (0)
#define MICROPY_DEBUG_PRINTERS      (1)
#define MICROPY_ENABLE_SCHEDULER    (1)
#define MICROPY_MODULE_BUILTIN_INIT (1)
// Printing debug to stderr may give tests which
// check stdout a chance to pass, etc.
#define MICROPY_DEBUG_PRINTER       (&mp_stderr_print)
#define MICROPY_READER_POSIX        (1)
#define MICROPY_USE_READLINE_HISTORY (1)
#define MICROPY_HELPER_REPL         (1)
#define MICROPY_REPL_EMACS_KEYS     (1)
#define MICROPY_REPL_AUTO_INDENT    (1)
#define MICROPY_HELPER_LEXER_UNIX   (1)
#define MICROPY_ENABLE_SOURCE_LINE  (1)
#ifndef MICROPY_FLOAT_IMPL
#define MICROPY_FLOAT_IMPL          (MICROPY_FLOAT_IMPL_DOUBLE)
#endif
#define MICROPY_LONGINT_IMPL        (MICROPY_LONGINT_IMPL_MPZ)
#ifndef MICROPY_STREAMS_NON_BLOCK
#define MICROPY_STREAMS_NON_BLOCK   (1)
#endif
#define MICROPY_STREAMS_POSIX_API   (1)
#define MICROPY_OPT_COMPUTED_GOTO   (1)
#ifndef MICROPY_OPT_CACHE_MAP_LOOKUP_IN_BYTECODE
#define MICROPY_OPT_CACHE_MAP_LOOKUP_IN_BYTECODE (1)
#endif
#define MICROPY_MODULE_WEAK_LINKS   (1)
#define MICROPY_CAN_OVERRIDE_BUILTINS (1)
#define MICROPY_VFS_POSIX_FILE      (1)
#define MICROPY_PY_FUNCTION_ATTRS   (1)
#define MICROPY_PY_DESCRIPTORS      (1)
#define MICROPY_PY_DELATTR_SETATTR  (1)
#define MICROPY_PY_BUILTINS_STR_UNICODE (1)
#define MICROPY_PY_BUILTINS_STR_CENTER (0)
#define MICROPY_PY_BUILTINS_STR_PARTITION (0)
#define MICROPY_PY_BUILTINS_STR_SPLITLINES (1)
#define MICROPY_PY_BUILTINS_MEMORYVIEW (1)
#define MICROPY_PY_BUILTINS_FROZENSET (1)
#define MICROPY_PY_BUILTINS_COMPILE (0)
#define MICROPY_PY_BUILTINS_NOTIMPLEMENTED (1)
#define MICROPY_PY_BUILTINS_INPUT   (1)
#define MICROPY_PY_BUILTINS_POW3    (1)
#define MICROPY_PY_BUILTINS_ROUND_INT    (1)
#define MICROPY_PY_MICROPYTHON_MEM_INFO (1)
#define MICROPY_PY_ALL_SPECIAL_METHODS (1)
#define MICROPY_PY_REVERSE_SPECIAL_METHODS (1)
#define MICROPY_PY_ARRAY_SLICE_ASSIGN (1)
#define MICROPY_PY_BUILTINS_SLICE_ATTRS (1)
#define MICROPY_PY_BUILTINS_SLICE_INDICES (1)
#define MICROPY_PY_SYS_EXIT         (1)
#define MICROPY_PY_SYS_ATEXIT       (1)
#if MICROPY_PY_SYS_SETTRACE
#define MICROPY_PERSISTENT_CODE_SAVE (1)
#define MICROPY_COMP_CONST (0)
#endif
#ifndef MICROPY_PY_SYS_PLATFORM
#if defined(__APPLE__) && defined(__MACH__)
    #define MICROPY_PY_SYS_PLATFORM  "darwin"
    #define LINUX_FRAME_BUFFER 0
#else
    #define MICROPY_PY_SYS_PLATFORM  "linux"
    #define LINUX_FRAME_BUFFER 1
#endif
#endif
#define MICROPY_PY_SYS_MAXSIZE      (1)
#define MICROPY_PY_SYS_STDFILES     (1)
#define MICROPY_PY_SYS_EXC_INFO     (1)
#define MICROPY_PY_COLLECTIONS_DEQUE (1)
#define MICROPY_PY_COLLECTIONS_ORDEREDDICT (1)
#ifndef MICROPY_PY_MATH_SPECIAL_FUNCTIONS
#define MICROPY_PY_MATH_SPECIAL_FUNCTIONS (1)
#endif
#define MICROPY_PY_MATH_ISCLOSE     (MICROPY_PY_MATH_SPECIAL_FUNCTIONS)
#define MICROPY_PY_CMATH            (1)
#define MICROPY_PY_IO_IOBASE        (1)
#define MICROPY_PY_IO_FILEIO        (1)
#define MICROPY_PY_GC_COLLECT_RETVAL (1)

#ifndef MICROPY_STACKLESS
#define MICROPY_STACKLESS           (0)
#define MICROPY_STACKLESS_STRICT    (0)
#endif

#define MICROPY_PY_LVGL             (1)
#define MICROPY_PY_LVGL_SDL         (0)
#define MICROPY_PY_LVGL_LODEPNG     (1)
#if LINUX_FRAME_BUFFER
    #define MICROPY_PY_LVGL_FB      (1)
#else
    #define MICROPY_PY_LVGL_FB      (0)
#endif

#define MICROPY_PY_OS_STATVFS       (1)
#define MICROPY_PY_UTIME            (1)
#define MICROPY_PY_UTIME_MP_HAL     (1)
#define MICROPY_PY_UERRNO           (1)
#define MICROPY_PY_UCTYPES          (1)
#define MICROPY_PY_UZLIB            (1)
#define MICROPY_PY_UJSON            (1)
#define MICROPY_PY_URE              (1)
#define MICROPY_PY_UHEAPQ           (1)
#define MICROPY_PY_UTIMEQ           (1)
#define MICROPY_PY_UHASHLIB         (1)
#if MICROPY_PY_USSL
#define MICROPY_PY_UHASHLIB_MD5     (1)
#define MICROPY_PY_UHASHLIB_SHA1    (1)
#define MICROPY_PY_UCRYPTOLIB       (1)
#endif
#define MICROPY_PY_UBINASCII        (1)
#define MICROPY_PY_UBINASCII_CRC32  (1)
#define MICROPY_PY_URANDOM          (1)
#ifndef MICROPY_PY_USELECT_POSIX
#define MICROPY_PY_USELECT_POSIX    (1)
#endif
#define MICROPY_PY_UWEBSOCKET       (1)
#define MICROPY_PY_MACHINE          (1)
#define MICROPY_PY_MACHINE_PULSE    (1)
#define MICROPY_MACHINE_MEM_GET_READ_ADDR   mod_machine_mem_get_addr
#define MICROPY_MACHINE_MEM_GET_WRITE_ADDR  mod_machine_mem_get_addr

#define MICROPY_FATFS_ENABLE_LFN       (1)
#define MICROPY_FATFS_RPATH            (2)
#define MICROPY_FATFS_MAX_SS           (4096)
#define MICROPY_FATFS_LFN_CODE_PAGE    437 /* 1=SFN/ANSI 437=LFN/U.S.(OEM) */

// Define to MICROPY_ERROR_REPORTING_DETAILED to get function, etc.
// names in exception messages (may require more RAM).
#define MICROPY_ERROR_REPORTING     (MICROPY_ERROR_REPORTING_DETAILED)
#define MICROPY_WARNINGS            (1)
#define MICROPY_ERROR_PRINTER       (&mp_stderr_print)
#define MICROPY_PY_STR_BYTES_CMP_WARN (1)

// VFS stat functions should return time values relative to 1970/1/1
#define MICROPY_EPOCH_IS_1970       (1)

extern const struct _mp_print_t mp_stderr_print;

#if !(defined(MICROPY_GCREGS_SETJMP) || defined(__x86_64__) || defined(__i386__) || defined(__thumb2__) || defined(__thumb__) || defined(__arm__))
// Fall back to setjmp() implementation for discovery of GC pointers in registers.
#define MICROPY_GCREGS_SETJMP (1)
#endif

#define MICROPY_ENABLE_EMERGENCY_EXCEPTION_BUF   (1)
#define MICROPY_EMERGENCY_EXCEPTION_BUF_SIZE  (256)
#define MICROPY_KBD_EXCEPTION       (1)
#define MICROPY_ASYNC_KBD_INTR      (1)

#define mp_type_fileio mp_type_vfs_posix_fileio
#define mp_type_textio mp_type_vfs_posix_textio

extern const struct _mp_obj_module_t mp_module_machine;
extern const struct _mp_obj_module_t mp_module_os;
extern const struct _mp_obj_module_t mp_module_uos_vfs;
extern const struct _mp_obj_module_t mp_module_uselect;
extern const struct _mp_obj_module_t mp_module_time;
extern const struct _mp_obj_module_t mp_module_termios;
extern const struct _mp_obj_module_t mp_module_socket;
extern const struct _mp_obj_module_t mp_module_ffi;
extern const struct _mp_obj_module_t mp_module_jni;
extern const struct _mp_obj_module_t mp_module_lvgl;
extern const struct _mp_obj_module_t mp_module_lvindev;
extern const struct _mp_obj_module_t mp_module_SDL;
extern const struct _mp_obj_module_t mp_module_fb;
extern const struct _mp_obj_module_t mp_module_lodepng;

#if MICROPY_PY_UOS_VFS
#define MICROPY_PY_UOS_DEF { MP_ROM_QSTR(MP_QSTR_uos), MP_ROM_PTR(&mp_module_uos_vfs) },
#else
#define MICROPY_PY_UOS_DEF { MP_ROM_QSTR(MP_QSTR_uos), MP_ROM_PTR(&mp_module_os) },
#endif
#if MICROPY_PY_FFI
#define MICROPY_PY_FFI_DEF { MP_ROM_QSTR(MP_QSTR_ffi), MP_ROM_PTR(&mp_module_ffi) },
#else
#define MICROPY_PY_FFI_DEF
#endif
#if MICROPY_PY_JNI
#define MICROPY_PY_JNI_DEF { MP_ROM_QSTR(MP_QSTR_jni), MP_ROM_PTR(&mp_module_jni) },
#else
#define MICROPY_PY_JNI_DEF
#endif
#if MICROPY_PY_UTIME
#define MICROPY_PY_UTIME_DEF { MP_ROM_QSTR(MP_QSTR_utime), MP_ROM_PTR(&mp_module_time) },
#else
#define MICROPY_PY_UTIME_DEF
#endif
#if MICROPY_PY_TERMIOS
#define MICROPY_PY_TERMIOS_DEF { MP_ROM_QSTR(MP_QSTR_termios), MP_ROM_PTR(&mp_module_termios) },
#else
#define MICROPY_PY_TERMIOS_DEF
#endif
#if MICROPY_PY_SOCKET
#define MICROPY_PY_SOCKET_DEF { MP_ROM_QSTR(MP_QSTR_usocket), MP_ROM_PTR(&mp_module_socket) },
#else
#define MICROPY_PY_SOCKET_DEF
#endif
#if MICROPY_PY_USELECT_POSIX
#define MICROPY_PY_USELECT_DEF { MP_ROM_QSTR(MP_QSTR_uselect), MP_ROM_PTR(&mp_module_uselect) },
#else
#define MICROPY_PY_USELECT_DEF
#endif

#if MICROPY_PY_LVGL
#ifndef MICROPY_INCLUDED_PY_MPSTATE_H
#define MICROPY_INCLUDED_PY_MPSTATE_H
#include "lib/lv_bindings/lvgl/src/misc/lv_gc.h"
#undef MICROPY_INCLUDED_PY_MPSTATE_H
#else
#include "lib/lv_bindings/lvgl/src/misc/lv_gc.h"
#endif
#define MICROPY_PY_LVGL_DEF { MP_OBJ_NEW_QSTR(MP_QSTR_lvgl), (mp_obj_t)&mp_module_lvgl },
    #if MICROPY_PY_LVGL_SDL
    #define MICROPY_PY_LVGL_SDL_DEF { MP_OBJ_NEW_QSTR(MP_QSTR_SDL), (mp_obj_t)&mp_module_SDL },
    #else
    #define MICROPY_PY_LVGL_SDL_DEF
    #endif
    #if MICROPY_PY_LVGL_FB
    #define MICROPY_PY_LVGL_FB_DEF { MP_OBJ_NEW_QSTR(MP_QSTR_fb), (mp_obj_t)&mp_module_fb },
    #else
    #define MICROPY_PY_LVGL_FB_DEF
    #endif
    #if MICROPY_PY_LVGL_LODEPNG
    #define MICROPY_PY_LVGL_LODEPNG_DEF { MP_OBJ_NEW_QSTR(MP_QSTR_lodepng), (mp_obj_t)&mp_module_lodepng },
    #else
    #define MICROPY_PY_LVGL_LODEPNG_DEF
    #endif
#else
    #define LV_ROOTS
    #define MICROPY_PY_LVGL_DEF
#endif

#define MICROPY_PORT_BUILTIN_MODULES \
    MICROPY_PY_FFI_DEF \
    MICROPY_PY_JNI_DEF \
    MICROPY_PY_UTIME_DEF \
    MICROPY_PY_SOCKET_DEF \
    { MP_ROM_QSTR(MP_QSTR_umachine), MP_ROM_PTR(&mp_module_machine) }, \
    MICROPY_PY_UOS_DEF \
    MICROPY_PY_USELECT_DEF \
    MICROPY_PY_TERMIOS_DEF \
    MICROPY_PY_LVGL_DEF \
    MICROPY_PY_LVGL_SDL_DEF \
    MICROPY_PY_LVGL_FB_DEF \
    MICROPY_PY_LVGL_LODEPNG_DEF

// type definitions for the specific machine

// For size_t and ssize_t
#include <unistd.h>

// assume that if we already defined the obj repr then we also defined types
#ifndef MICROPY_OBJ_REPR
#ifdef __LP64__
typedef long mp_int_t; // must be pointer size
typedef unsigned long mp_uint_t; // must be pointer size
#else
// These are definitions for machines where sizeof(int) == sizeof(void*),
// regardless of actual size.
typedef int mp_int_t; // must be pointer size
typedef unsigned int mp_uint_t; // must be pointer size
#endif
#endif

// Cannot include <sys/types.h>, as it may lead to symbol name clashes
#if _FILE_OFFSET_BITS == 64 && !defined(__LP64__)
typedef long long mp_off_t;
#else
typedef long mp_off_t;
#endif

void mp_unix_alloc_exec(size_t min_size, void **ptr, size_t *size);
void mp_unix_free_exec(void *ptr, size_t size);
void mp_unix_mark_exec(void);
#define MP_PLAT_ALLOC_EXEC(min_size, ptr, size) mp_unix_alloc_exec(min_size, ptr, size)
#define MP_PLAT_FREE_EXEC(ptr, size) mp_unix_free_exec(ptr, size)
#ifndef MICROPY_FORCE_PLAT_ALLOC_EXEC
// Use MP_PLAT_ALLOC_EXEC for any executable memory allocation, including for FFI
// (overriding libffi own implementation)
#define MICROPY_FORCE_PLAT_ALLOC_EXEC (1)
#endif

#ifdef __linux__
// Can access physical memory using /dev/mem
#define MICROPY_PLAT_DEV_MEM  (1)
#endif

// Assume that select() call, interrupted with a signal, and erroring
// with EINTR, updates remaining timeout value.
#define MICROPY_SELECT_REMAINING_TIME (1)

#ifdef __ANDROID__
#include <android/api-level.h>
#if __ANDROID_API__ < 4
// Bionic libc in Android 1.5 misses these 2 functions
#define MP_NEED_LOG2 (1)
#define nan(x) NAN
#endif
#endif

#define MICROPY_PORT_BUILTINS \
    { MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&mp_builtin_open_obj) },

#define MP_STATE_PORT MP_STATE_VM

#if MICROPY_PY_BLUETOOTH
#if MICROPY_BLUETOOTH_BTSTACK
struct _mp_bluetooth_btstack_root_pointers_t;
#define MICROPY_BLUETOOTH_ROOT_POINTERS struct _mp_bluetooth_btstack_root_pointers_t *bluetooth_btstack_root_pointers;
#endif
#if MICROPY_BLUETOOTH_NIMBLE
struct _mp_bluetooth_nimble_root_pointers_t;
struct _mp_bluetooth_nimble_malloc_t;
#define MICROPY_BLUETOOTH_ROOT_POINTERS struct _mp_bluetooth_nimble_malloc_t *bluetooth_nimble_memory; struct _mp_bluetooth_nimble_root_pointers_t *bluetooth_nimble_root_pointers;
#endif
#else
#define MICROPY_BLUETOOTH_ROOT_POINTERS
#endif

#define MICROPY_PORT_ROOT_POINTERS \
    LV_ROOTS \
    void *mp_lv_user_data; \
    const char *readline_hist[50]; \
    void *mmap_region_head; \
    MICROPY_BLUETOOTH_ROOT_POINTERS \

// We need to provide a declaration/definition of alloca()
// unless support for it is disabled.
#if !defined(MICROPY_NO_ALLOCA) || MICROPY_NO_ALLOCA == 0
#ifdef __FreeBSD__
#include <stdlib.h>
#else
#include <alloca.h>
#endif
#endif

// From "man readdir": "Under glibc, programs can check for the availability
// of the fields [in struct dirent] not defined in POSIX.1 by testing whether
// the macros [...], _DIRENT_HAVE_D_TYPE are defined."
// Other libc's don't define it, but proactively assume that dirent->d_type
// is available on a modern *nix system.
#ifndef _DIRENT_HAVE_D_TYPE
#define _DIRENT_HAVE_D_TYPE (1)
#endif
// This macro is not provided by glibc but we need it so ports that don't have
// dirent->d_ino can disable the use of this field.
#ifndef _DIRENT_HAVE_D_INO
#define _DIRENT_HAVE_D_INO (1)
#endif

#ifndef __APPLE__
// For debugging purposes, make printf() available to any source file.
#include <stdio.h>
#endif

#if MICROPY_PY_THREAD
#define MICROPY_BEGIN_ATOMIC_SECTION() (mp_thread_unix_begin_atomic_section(), 0xffffffff)
#define MICROPY_END_ATOMIC_SECTION(x) (void)x; mp_thread_unix_end_atomic_section()
#endif

#define MICROPY_EVENT_POLL_HOOK \
    do { \
        extern void mp_handle_pending(bool); \
        mp_handle_pending(true); \
        mp_hal_delay_us(500); \
    } while (0);

#include <sched.h>
#define MICROPY_UNIX_MACHINE_IDLE sched_yield();

#endif // MICROPY_UNIX_MINIMAL
