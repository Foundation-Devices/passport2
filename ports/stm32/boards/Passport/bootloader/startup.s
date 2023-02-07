/*
  SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
  SPDX-License-Identifier: GPL-3.0-or-later

  SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
  SPDX-License-Identifier: GPL-3.0-only
*/
    .thumb
    .syntax unified

    .global Reset_Handler
    .type Reset_Handler, %function

Reset_Handler:

    /* Load the stack pointer */
    ldr  sp, =_estack

    /* Initialise the data section */
    ldr  r1, =_sidata
    ldr  r2, =_sdata
    ldr  r3, =_edata
    b    .data_copy_entry
.data_copy_loop:
    ldr  r0, [r1], #4 /* Should be 4-aligned to be as fast as possible */
    str  r0, [r2], #4
.data_copy_entry:
    cmp  r2, r3
    bcc  .data_copy_loop

    /* Zero out the BSS section */
    movs r0, #0
    ldr  r1, =_sbss
    ldr  r2, =_ebss
    b    .bss_zero_entry
.bss_zero_loop:
    str  r0, [r1], #4 /* Should be 4-aligned to be as fast as possible */
.bss_zero_entry:
    cmp  r1, r2
    bcc  .bss_zero_loop

    /* Initialise the sram section */
    ldr  r1, =_siram
    ldr  r2, =_sram
    ldr  r3, =_eram
    b    .ram_copy_entry
.ram_copy_loop:
    ldr  r0, [r1], #4 /* Should be 4-aligned to be as fast as possible */
    str  r0, [r2], #4
.ram_copy_entry:
    cmp  r2, r3
    bcc  .ram_copy_loop

    bl      main

    /* Get pointer to firmware code
     * load R1 with _bl_fw_base value: start of firmware,
     * _bl_fw_base should be defined by the linker script.
     */
    ldr     r1, =_bl_fw_base

    /* set stack pointer to their preference */
    ldr     r0, [r1]
    mov     sp, r0

    /* Disabled
     * We cannot change to user mode here because the micropython code
     * depends on being in supervisor mode. SystemInit() is invoked
     * from the Reset_Handler() and the vector table (along with other
     * SCB accesses) is set at the start of stm32_main()...both
     * important things in the startup processing.
     */
    /* We are in supervisor mode out of reset...drop down to user mode */
/*
    mrs     r3, CONTROL
    orr.w   r3, r3, #1
    msr     CONTROL, r3
*/
    /* Read reset vector, and jump to it. */
    mov     r0, 1           /* set reset_mode arg: 1=normal? */
    ldr     lr, [r1, 4]
    bx      lr

    .end
