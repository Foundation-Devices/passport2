// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(not(feature = "std"), no_std)]
#![feature(alloc_error_handler)]
#![allow(non_camel_case_types)]

extern crate alloc;

pub mod ur;
pub mod bitcoin;

/// cbindgen:ignore
#[cfg(not(feature = "std"))]
mod stdout;

#[cfg(not(feature = "std"))]
pub struct SystemAllocator;

#[cfg(not(feature = "std"))]
unsafe impl core::alloc::GlobalAlloc for SystemAllocator {
    unsafe fn alloc(&self, layout: core::alloc::Layout) -> *mut u8 {
        extern "C" {
            fn malloc(size: usize) -> *mut core::ffi::c_void;
        }

        malloc(layout.size()) as *mut u8
    }

    unsafe fn dealloc(&self, ptr: *mut u8, _: core::alloc::Layout) {
        extern "C" {
            fn free(data: *mut core::ffi::c_void);
        }

        free(ptr as *mut core::ffi::c_void)
    }
}

#[cfg(not(feature = "std"))]
#[global_allocator]
static mut SYSTEM_ALLOCATOR: SystemAllocator = SystemAllocator;

#[cfg(not(feature = "std"))]
#[alloc_error_handler]
fn alloc_error_handler(layout: core::alloc::Layout) -> ! {
    use core::fmt::Write;

    let mut stdout = stdout::Stdout;
    writeln!(stdout, "could not allocate: {:?}", layout).ok();

    loop {}
}

#[panic_handler]
#[cfg(all(not(feature = "std"), not(test)))]
fn panic_handler(info: &core::panic::PanicInfo) -> ! {
    use core::fmt::Write;

    let mut stdout = stdout::Stdout;
    writeln!(stdout, "{}", info).ok();

    loop {}
}
