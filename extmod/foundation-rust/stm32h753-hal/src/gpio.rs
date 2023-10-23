// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use core::convert::Infallible;
use core::marker::PhantomData;

use embedded_hal::digital::v2::OutputPin;
use stm32h7::stm32h753::{
    gpioa::RegisterBlock, GPIOA, GPIOB, GPIOC, GPIOD, GPIOE, GPIOF, GPIOG,
    GPIOH, GPIOI, GPIOJ, GPIOK,
};

pub trait GpioExt {
    type Parts;

    fn split(self) -> Self::Parts;
}

pub struct Pin<const P: char, const N: usize, M>(PhantomData<M>);

impl<const P: char, const N: usize, M> Pin<P, N, M> {
    const fn register_block() -> *const RegisterBlock {
        match P {
            'A' => GPIOA::PTR,
            'B' => GPIOB::PTR,
            'C' => GPIOC::PTR,
            'D' => GPIOD::PTR,
            'E' => GPIOE::PTR,
            'F' => GPIOF::PTR,
            'G' => GPIOG::PTR,
            'H' => GPIOH::PTR,
            'I' => GPIOI::PTR,
            'J' => GPIOJ::PTR,
            'K' => GPIOK::PTR,
            _ => panic!("Non-existent GPIO peripheral"),
        }
    }
}

impl<const P: char, const N: usize> Pin<P, N, Floating> {
    /// # Safety
    ///
    /// This is not atomic, so if called from multiple threads on multiple pins
    /// of the same peripheral bits may get lost.
    ///
    /// Not a problem with mode changing though as it is mostly done on
    /// initialization.
    pub unsafe fn change_mode<M: Mode>(self) -> Pin<P, N, M> {
        let offset = 2 * N;
        let mask = 0b11 << offset;

        // FIXME: For this to be completely safe it needs to be written
        // atomically (STREX/LDREX).
        //
        // SAFETY: Only writes the bits related to this Pin.
        unsafe {
            let periph = &*Self::register_block();
            periph
                .moder
                .modify(|r, w| w.bits(((r.bits()) & !mask) | M::MODER))
        }

        Pin(PhantomData)
    }

    /// # Safety
    ///
    /// This operation is not atomic.
    ///
    /// See [`change_mode`].
    pub unsafe fn into_output(self) -> Pin<P, N, Output> {
        self.change_mode::<Output>()
    }
}

impl<const P: char, const N: usize> OutputPin for Pin<P, N, Output> {
    type Error = Infallible;

    fn set_low(&mut self) -> Result<(), Self::Error> {
        // SAFETY: stateless register, write 1 to reset.
        unsafe {
            (&*Self::register_block())
                .bsrr
                .write(|w| w.bits(1 << (16 + N)))
        }

        Ok(())
    }

    fn set_high(&mut self) -> Result<(), Self::Error> {
        unsafe { (&*Self::register_block()).bsrr.write(|w| w.bits(1 << N)) }

        Ok(())
    }
}

// Mode type states.
pub struct Floating;
pub struct Input;
pub struct Output;
pub struct AlternateFunction;
pub struct AnalogMode;

pub trait Mode {
    const MODER: u32;
}

impl Mode for Input {
    const MODER: u32 = 0b00;
}

impl Mode for Output {
    const MODER: u32 = 0b01;
}

impl Mode for AlternateFunction {
    const MODER: u32 = 0b10;
}

impl Mode for AnalogMode {
    const MODER: u32 = 0b11;
}

pub mod gpioe {
    use core::marker::PhantomData;

    use stm32h7::stm32h753::{rcc, GPIOE};

    use crate::gpio::{Floating, GpioExt, Pin};
    use crate::rcc::Enable;

    pub struct Parts {
        pub pe11: Pin<'E', 11, Floating>,
    }

    impl GpioExt for GPIOE {
        type Parts = Parts;

        fn split(self) -> Self::Parts {
            Parts {
                pe11: Pin(PhantomData),
            }
        }
    }

    impl Enable for GPIOE {
        fn enable(&self, rcc: &rcc::RegisterBlock) {
            rcc.ahb4enr.modify(|_, w| w.gpioeen().set_bit())
        }
    }

    pub type PE11<M> = Pin<'E', 11, M>;
}
