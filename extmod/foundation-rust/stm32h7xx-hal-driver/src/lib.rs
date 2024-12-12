// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#![no_std]

use cmsis_device_h7_sys::SPI_TypeDef;
use core::{
    num::{NonZeroU32, TryFromIntError},
    ptr,
};
use embedded_hal::spi::{Operation, SpiBus};
use stm32h7xx_hal_driver_sys::{
    HAL_GetTick, HAL_LockTypeDef, HAL_SPI_Init, HAL_SPI_Receive,
    HAL_SPI_StateTypeDef, HAL_SPI_Transmit, HAL_StatusTypeDef,
    HAL_StatusTypeDef::HAL_OK, SPI_HandleTypeDef, SPI_InitTypeDef,
    HAL_MAX_DELAY, HAL_SPI_ERROR_NONE,
};

/// Re-export of the [`stm32h7xx_hal_driver_sys`] crate as sys.
pub use stm32h7xx_hal_driver_sys as sys;

/// SAFETY: Performs non-atomic read-modify-write sequence, so the user
/// must make sure this is not written by different threads or
/// interrupts at the same "time".
///
/// NOTE:
///
/// The functions enabling RCC peripheral clocks read the register just
/// after, don't remove it, this is a necessary delay after enabling
/// the clock.
pub mod rcc {
    use cmsis_device_h7_sys::{RCC, RCC_AHB4ENR_GPIOEEN, RCC_APB2ENR_SPI4EN};
    use core::ptr;

    #[inline]
    unsafe fn set_bit(ptr: *mut u32, bit: u32) {
        let mut tmpreg = ptr::read_volatile(ptr);
        tmpreg |= bit;
        ptr::write_volatile(ptr, tmpreg);
    }

    #[inline]
    unsafe fn read_bit(ptr: *mut u32, bit: u32) -> u32 {
        let tmpreg = ptr::read_volatile(ptr);
        tmpreg & bit
    }

    pub unsafe fn gpioe_clk_enable() {
        let ahb4enr = ptr::addr_of_mut!((*RCC).AHB4ENR);
        set_bit(ahb4enr, RCC_AHB4ENR_GPIOEEN);
        read_bit(ahb4enr, RCC_AHB4ENR_GPIOEEN);
    }

    pub unsafe fn spi4_clk_enable() {
        let apb2enr = ptr::addr_of_mut!((*RCC).APB2ENR);
        set_bit(apb2enr, RCC_APB2ENR_SPI4EN);
        read_bit(apb2enr, RCC_APB2ENR_SPI4EN);
    }
}

pub mod gpio {
    use cmsis_device_h7_sys::GPIO_TypeDef;
    use core::convert::Infallible;
    use stm32h7xx_hal_driver_sys::{
        GPIO_InitTypeDef, GPIO_PinState, HAL_GPIO_Init, HAL_GPIO_WritePin,
        GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, GPIO_SPEED_FREQ_HIGH,
    };

    /// General purpose output pin.
    #[derive(Debug)]
    pub struct OutputPin {
        instance: *mut GPIO_TypeDef,
        pin: u16,
    }

    impl OutputPin {
        /// SAFETY:
        ///
        /// - User must make sure to not initialize the same pin twice.
        /// - The peripheral clock must be enabled for this function
        /// to take effect.
        pub unsafe fn new(instance: *mut GPIO_TypeDef, pin: u16) -> Self {
            let mut init = GPIO_InitTypeDef {
                Pin: u32::from(pin),
                Mode: GPIO_MODE_OUTPUT_PP,
                Pull: GPIO_NOPULL,
                Speed: GPIO_SPEED_FREQ_HIGH,
                Alternate: 0,
            };

            // SAFETY: The user must make sure that we are only initializing the
            // same pin once, and that the `instance` peripheral is enabled
            // on the RCC.
            unsafe {
                HAL_GPIO_Init(instance, (&mut init) as *mut GPIO_InitTypeDef);
            }

            Self { instance, pin }
        }
    }

    impl embedded_hal::digital::ErrorType for OutputPin {
        type Error = Infallible;
    }

    impl embedded_hal::digital::OutputPin for OutputPin {
        fn set_low(&mut self) -> Result<(), Self::Error> {
            // SAFETY: Pin and instance should be initialized at this point.
            unsafe {
                HAL_GPIO_WritePin(
                    self.instance,
                    self.pin,
                    GPIO_PinState::GPIO_PIN_RESET,
                )
            }

            Ok(())
        }

        fn set_high(&mut self) -> Result<(), Self::Error> {
            // SAFETY: Pin and instance should be initialized at this point.
            unsafe {
                HAL_GPIO_WritePin(
                    self.instance,
                    self.pin,
                    GPIO_PinState::GPIO_PIN_SET,
                )
            }

            Ok(())
        }
    }
}

#[inline(always)]
pub fn get_tick() -> u32 {
    unsafe { HAL_GetTick() }
}

/// SPI driver handle.
#[derive(Debug)]
pub struct Spi {
    handle: SPI_HandleTypeDef,
}

impl Spi {
    /// Creates a new [`Spi`] driver instance.
    pub unsafe fn new(
        instance: *mut SPI_TypeDef,
        init: SPI_InitTypeDef,
    ) -> Result<Spi, Error> {
        let mut spi = Spi {
            handle: SPI_HandleTypeDef {
                Instance: instance,
                Init: init,
                pTxBuffPtr: ptr::null_mut(),
                TxXferSize: 0,
                TxXferCount: 0,
                pRxBuffPtr: ptr::null_mut(),
                RxXferSize: 0,
                RxXferCount: 0,
                CRCSize: 0,
                RxISR: None,
                TxISR: None,
                hdmatx: ptr::null_mut(),
                hdmarx: ptr::null_mut(),
                Lock: HAL_LockTypeDef::HAL_UNLOCKED,
                State: HAL_SPI_StateTypeDef::HAL_SPI_STATE_RESET,
                ErrorCode: HAL_SPI_ERROR_NONE,
            },
        };

        let status = HAL_SPI_Init(&mut spi.handle as *mut SPI_HandleTypeDef);
        if status != HAL_OK {
            let code = NonZeroU32::new(spi.handle.ErrorCode);
            Err(Error::Hal { status, code })
        } else {
            Ok(spi)
        }
    }
}

/// Errors that can happen when using the SPI peripheral.
#[derive(Debug, Clone, Copy)]
pub enum Error {
    /// We don't handle cases where the transfer is bigger than u16::MAX since
    /// that is the limit of DMA.  If needed just modify the code to perform
    /// chunks of transfers.  MDMA Could handle this automagically I believe.
    TransferTooBig(TryFromIntError),
    /// HAL Error.
    Hal {
        status: HAL_StatusTypeDef::Type,
        code: Option<NonZeroU32>,
    },
}

impl From<TryFromIntError> for Error {
    fn from(e: TryFromIntError) -> Self {
        Self::TransferTooBig(e)
    }
}

impl embedded_hal::spi::Error for Error {
    fn kind(&self) -> embedded_hal::spi::ErrorKind {
        use embedded_hal::spi::ErrorKind;

        match self {
            Self::TransferTooBig(_) => ErrorKind::Other,
            Self::Hal { .. } => ErrorKind::Other,
        }
    }
}

impl embedded_hal::spi::ErrorType for Spi {
    type Error = Error;
}

impl SpiBus for Spi {
    fn read(&mut self, words: &mut [u8]) -> Result<(), Self::Error> {
        let status = unsafe {
            HAL_SPI_Receive(
                &mut self.handle as *mut SPI_HandleTypeDef,
                words.as_mut_ptr(),
                u16::try_from(words.len())?,
                HAL_MAX_DELAY,
            )
        };

        if status != HAL_OK {
            let code = NonZeroU32::new(self.handle.ErrorCode);
            return Err(Error::Hal { status, code });
        }

        Ok(())
    }

    fn write(&mut self, words: &[u8]) -> Result<(), Self::Error> {
        let status = unsafe {
            HAL_SPI_Transmit(
                &mut self.handle as *mut SPI_HandleTypeDef,
                words.as_ptr() as *mut u8,
                u16::try_from(words.len())?,
                HAL_MAX_DELAY,
            )
        };

        if status != HAL_OK {
            let code = NonZeroU32::new(self.handle.ErrorCode);
            return Err(Error::Hal { status, code });
        }

        Ok(())
    }

    fn transfer(
        &mut self,
        _read: &mut [u8],
        _write: &[u8],
    ) -> Result<(), Self::Error> {
        Ok(())
    }

    fn transfer_in_place(
        &mut self,
        _words: &mut [u8],
    ) -> Result<(), Self::Error> {
        Ok(())
    }

    fn flush(&mut self) -> Result<(), Self::Error> {
        Ok(())
    }
}

// NOTE: Perhaps this doesn't belong in this crate as this is
// application specific.
#[derive(Debug)]
pub struct SpiDevice {
    spi: Spi,
    cs: gpio::OutputPin,
}

impl SpiDevice {
    pub fn new(spi: Spi, cs: gpio::OutputPin) -> Self {
        Self { spi, cs }
    }
}

impl embedded_hal::spi::ErrorType for SpiDevice {
    type Error = Error;
}

impl embedded_hal::spi::SpiDevice for SpiDevice {
    fn transaction(
        &mut self,
        operations: &mut [Operation<'_, u8>],
    ) -> Result<(), Self::Error> {
        use embedded_hal::digital::OutputPin;

        self.cs.set_low().ok();

        for op in operations {
            match op {
                Operation::Read(buf) => self.spi.read(buf)?,
                Operation::Write(buf) => self.spi.write(buf)?,
                Operation::DelayNs(_) => {}
                Operation::Transfer(read, write) => {
                    self.spi.transfer(read, write)?
                }
                Operation::TransferInPlace(buf) => {
                    self.spi.transfer_in_place(buf)?
                }
            }
        }

        self.spi.flush()?;
        self.cs.set_high().ok();

        Ok(())
    }
}
