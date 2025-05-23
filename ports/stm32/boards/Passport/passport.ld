/*
   SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
   SPDX-License-Identifier: GPL-3.0-or-later

   GNU linker script for STM32H753
*/

/* Specify the memory areas */
MEMORY
{
    FLASH (rx)      : ORIGIN = BL_FW_BASE,                  LENGTH = BL_FW_END - BL_FW_BASE
    DTCM (xrw)      : ORIGIN = 0x20000000,                  LENGTH = 128K
    RAM (xrw)       : ORIGIN = 0x24000000,                  LENGTH = 512K           /* AXI SRAM */
    RAM_D2 (rw)     : ORIGIN = 0x30000000,                  LENGTH = 288K           /* D2 SRAM (128K + 128 + 32K) */
    SRAM4 (xrw)     : ORIGIN = 0x38000000,                  LENGTH = 64K
}

ENTRY(Reset_Handler)
ASSERT(ORIGIN(FLASH) + LENGTH(FLASH) == BL_FW_END, "invalid firmware length")

/* produce a link error if there is not this amount of RAM for these sections */
_minimum_stack_size = 2K;
_minimum_heap_size = 16K;

/* Define the stack. The stack is full descending so begins just above last byte
   of RAM. Note that EABI requires the stack to be 8-byte aligned for a call. */
_estack = ORIGIN(RAM) + LENGTH(RAM) - _estack_reserve;
_sstack = _estack - 48K; /* tunable */

/* RAM extents for the garbage collector */
_ram_start = ORIGIN(RAM);
_ram_end = ORIGIN(RAM) + LENGTH(RAM);
_heap_start = _ebss; /* heap starts just after statically allocated memory */
_heap_end = _sstack;

SECTIONS
{
    /* The startup code goes first into FLASH */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector)) /* Startup code */

        . = ALIGN(4);
    } >FLASH

    /* The program code and other data goes into FLASH */
    .text :
    {
        . = ALIGN(4);
        *(.text*)          /* .text* sections (code) */
        *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
    /*  *(.glue_7)   */    /* glue arm to thumb code */
    /*  *(.glue_7t)  */    /* glue thumb to arm code */

        . = ALIGN(4);
        _etext = .;        /* define a global symbol at end of code */
    } >FLASH

    /* D2 SRAM section, generally used for DMA, it's slower than the DTCM and the
       AXI SRAM but faster than those two for DMA on D2 peripherals. Has to be
       manually turned on in the RCC */
    .ram_d2 (NOLOAD) : {
        KEEP(*(.dma_buffers))
    } >RAM_D2

    .dtcm (NOLOAD) : {
        KEEP(*(.dtcm))
    } >DTCM

    .sram4 (NOLOAD) : {
        KEEP(*(.sram4))
    } >SRAM4

    INCLUDE common_extratext_data_in_flash.ld
    INCLUDE common_bss_heap_stack.ld
}
