// SPDX-FileCopyrightText: 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use core::{
    cell::RefCell,
    ptr::{addr_of_mut, NonNull},
    slice,
};
use embedded_storage::nor_flash::{NorFlash, ReadNorFlash};
use embedded_storage_nom::rc::{Rc, RcInner};
use embedded_storage_redundant::RedundantRead;
use once_cell::unsync::Lazy;

/// cbindgen:ignore
#[cfg(all(target_os = "none", target_arch = "arm"))]
type Storage =
    RedundantRead<w25q64jv::W25Q64JV<stm32h7xx_hal_driver::SpiDevice>, 3, 1024>;

/// cbindgen:ignore
#[cfg(not(target_arch = "arm"))]
type Storage = RedundantRead<embedded_storage_fs::File<1, 1, 4096>, 3, 1024>;

// The on-device flash storage device.
//
// This assumes the code is single threaded and this is not used during
// interrupts.
//
// If we reach that point in the future, I'd recommend a Mutex.
/// cbindgen:ignore
#[cfg(all(target_os = "none", target_arch = "arm"))]
static mut STORAGE_RC: Lazy<RcInner<RefCell<Storage>>> = Lazy::new(|| {
    use cmsis_device_h7_sys::{GPIOE, SPI4};
    use stm32h7xx_hal_driver::{gpio, rcc, sys, Spi, SpiDevice};
    use w25q64jv::W25Q64JV;

    unsafe {
        rcc::gpioe_clk_enable();
        rcc::spi4_clk_enable();
    }

    let cs = unsafe { gpio::OutputPin::new(GPIOE, sys::GPIO_PIN_11) };

    unsafe {
        let mut init = sys::GPIO_InitTypeDef {
            Pin: u32::from(
                sys::GPIO_PIN_12 | sys::GPIO_PIN_13 | sys::GPIO_PIN_14,
            ),
            Mode: sys::GPIO_MODE_AF_PP,
            Pull: sys::GPIO_PULLDOWN,
            Speed: sys::GPIO_SPEED_FREQ_HIGH,
            Alternate: u32::from(sys::GPIO_AF5_SPI4),
        };

        sys::HAL_GPIO_Init(GPIOE, (&mut init) as *mut sys::GPIO_InitTypeDef)
    }

    let init = sys::SPI_InitTypeDef {
        Mode: sys::SPI_MODE_MASTER,
        Direction: sys::SPI_DIRECTION_2LINES,
        DataSize: sys::SPI_DATASIZE_8BIT,
        CLKPolarity: sys::SPI_POLARITY_LOW,
        CLKPhase: sys::SPI_PHASE_1EDGE,
        NSS: sys::SPI_NSS_SOFT,
        // NOTE: See ports/stm32/boards/Passport/frequency.c for the clock
        // value of SPI4-5, it uses the PCLK2 clock, and it currently is
        // 120 MHz, so divided by 16 provides a clock of 7.5 MHz.
        BaudRatePrescaler: sys::SPI_BAUDRATEPRESCALER_16,
        FirstBit: sys::SPI_FIRSTBIT_MSB,
        TIMode: sys::SPI_TIMODE_DISABLE,
        CRCCalculation: sys::SPI_CRCCALCULATION_DISABLE,
        CRCPolynomial: 0,
        CRCLength: 0,
        NSSPMode: 0,
        NSSPolarity: 0,
        FifoThreshold: 0,
        TxCRCInitializationPattern: 0,
        RxCRCInitializationPattern: 0,
        MasterSSIdleness: 0,
        MasterInterDataIdleness: 0,
        MasterReceiverAutoSusp: 0,
        MasterKeepIOState: 0,
        IOSwap: 0,
    };

    // SAFETY:
    //
    // The stm32h7xx_hal_driver crate does not guarantee that any other
    // place in the entire codebase won't initialize the same peripheral
    // twice, so it is up to us to keep that in mind.
    //
    // NOTE:
    //
    // We use expect here since this shouldn't fail, if it fails it is a
    // logic error. There's no way to recover from this anyway as the
    // flash is required.
    let spi4 = unsafe {
        Spi::new(SPI4, init).expect("failed SPI4 (flash) initialization")
    };

    let spi_device = SpiDevice::new(spi4, cs);
    RcInner::new(RefCell::new(RedundantRead::new(
        W25Q64JV::new(spi_device),
        9,
    )))
});

// The flash storage for the simulator.
//
// Technically RedundantRead is not needed, but to test this piece of code
// that is used on device is kept here.
/// cbindgen:ignore
#[cfg(not(target_arch = "arm"))]
static mut STORAGE_RC: Lazy<RcInner<RefCell<Storage>>> = Lazy::new(|| {
    use embedded_storage_fs::File;

    // NOTE: It is fine to panic here as this code is for the simulator.
    //
    // The capacity is 8 MiB as in the hardware.
    let file = File::open("spi_flash.bin", 8 * 1024 * 1024)
        .expect("Could not open SPI flash file");
    RcInner::new(RefCell::new(RedundantRead::new(file, 3)))
});

/// cbindgen:ignore
pub static mut STORAGE: Lazy<Rc<RefCell<Storage>>> = Lazy::new(|| unsafe {
    Rc::from_inner(NonNull::from(Lazy::force_mut(&mut *addr_of_mut!(
        STORAGE_RC
    ))))
});

/// Read from the flash storage.
#[export_name = "foundation_flash_read"]
pub extern "C" fn read(offset: u32, data: *mut u8, len: usize) -> bool {
    let mut flash = unsafe { STORAGE.borrow_mut() };
    let buf = unsafe { slice::from_raw_parts_mut(data, len) };

    if let Err(_) = flash.read(offset, buf) {
        false
    } else {
        true
    }
}

/// Write to the flash storage.
#[export_name = "foundation_flash_write"]
pub extern "C" fn write(offset: u32, data: *const u8, len: usize) -> bool {
    let mut flash = unsafe { STORAGE.borrow_mut() };
    let buf = unsafe { slice::from_raw_parts(data, len) };

    if let Err(_) = flash.write(offset, buf) {
        false
    } else {
        true
    }
}

/// Erase a sector of the flash storage.
#[export_name = "foundation_flash_sector_erase"]
pub extern "C" fn sector_erase(offset: u32) -> bool {
    let mut flash = unsafe { STORAGE.borrow_mut() };

    #[cfg(target_arch = "arm")]
    {
        if flash.as_mut_inner().sector_erase(offset).is_err() {
            return false;
        }
    }

    #[cfg(not(target_arch = "arm"))]
    {
        // Erase 4 KiB.
        if flash
            .as_mut_inner()
            .erase(offset, offset + (4 * 1024))
            .is_err()
        {
            return false;
        }
    }

    true
}

/// Erase a block of the flash storage.
#[export_name = "foundation_flash_block_erase"]
pub extern "C" fn block_erase(offset: u32) -> bool {
    let mut flash = unsafe { STORAGE.borrow_mut() };

    #[cfg(target_arch = "arm")]
    {
        if flash.as_mut_inner().block_erase_64kib(offset).is_err() {
            return false;
        }
    }

    #[cfg(not(target_arch = "arm"))]
    {
        // Erase 64 KiB.
        if flash
            .as_mut_inner()
            .erase(offset, offset + (64 * 1024))
            .is_err()
        {
            return false;
        }
    }

    true
}

/// Sets result to `true` if the flash is busy with a write or erase
/// operation.
#[export_name = "foundation_flash_is_busy"]
pub extern "C" fn is_busy(result: &mut bool) -> bool {
    *result = false;

    #[cfg(target_arch = "arm")]
    {
        let mut flash = unsafe { STORAGE.borrow_mut() };

        match flash.as_mut_inner().read_status_1() {
            Ok(status) => *result = status.contains(w25q64jv::Status1::BUSY),
            Err(_) => return false,
        }
    }

    true
}

/// Wait until flash storage is not busy.
#[export_name = "foundation_flash_wait_done"]
pub extern "C" fn wait_done() -> bool {
    #[cfg(target_arch = "arm")]
    {
        let mut flash = unsafe { STORAGE.borrow_mut() };

        if let Err(_) = flash.as_mut_inner().flush() {
            return false;
        }
    }

    true
}
