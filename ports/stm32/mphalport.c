#include <string.h>

#include "py/runtime.h"
#include "py/stream.h"
#include "py/mperrno.h"
#include "py/mphal.h"
#include "extmod/misc.h"
#if MICROPY_HW_ENABLE_USB
#include "usb.h"
#endif
#include "uart.h"

// this table converts from HAL_StatusTypeDef to POSIX errno
const byte mp_hal_status_to_errno_table[4] = {
    [HAL_OK] = 0,
    [HAL_ERROR] = MP_EIO,
    [HAL_BUSY] = MP_EBUSY,
    [HAL_TIMEOUT] = MP_ETIMEDOUT,
};

NORETURN void mp_hal_raise(HAL_StatusTypeDef status) {
    mp_raise_OSError(mp_hal_status_to_errno_table[status]);
}

MP_WEAK uintptr_t mp_hal_stdio_poll(uintptr_t poll_flags) {
    uintptr_t ret = 0;
    if (MP_STATE_PORT(pyb_stdio_uart) != NULL) {
        mp_obj_t pyb_stdio_uart = MP_OBJ_FROM_PTR(MP_STATE_PORT(pyb_stdio_uart));
        int errcode;
        const mp_stream_p_t *stream_p = mp_get_stream(pyb_stdio_uart);
        ret = stream_p->ioctl(pyb_stdio_uart, MP_STREAM_POLL, poll_flags, &errcode);
    }
    return ret | mp_uos_dupterm_poll(poll_flags);
}

MP_WEAK int mp_hal_stdin_rx_chr(void) {
    for (;;) {
        #if 0
        #ifdef USE_HOST_MODE
        pyb_usb_host_process();
        int c = pyb_usb_host_get_keyboard();
        if (c != 0) {
            return c;
        }
        #endif
        #endif
        if (MP_STATE_PORT(pyb_stdio_uart) != NULL && uart_rx_any(MP_STATE_PORT(pyb_stdio_uart))) {
            return uart_rx_char(MP_STATE_PORT(pyb_stdio_uart));
        }
        int dupterm_c = mp_uos_dupterm_rx_chr();
        if (dupterm_c >= 0) {
            return dupterm_c;
        }
        MICROPY_EVENT_POLL_HOOK
    }
}

void mp_hal_stdout_tx_str(const char *str) {
    mp_hal_stdout_tx_strn(str, strlen(str));
}

MP_WEAK void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    if (MP_STATE_PORT(pyb_stdio_uart) != NULL) {
        uart_tx_strn(MP_STATE_PORT(pyb_stdio_uart), str, len);
    }
    #if 0 && defined(USE_HOST_MODE) && MICROPY_HW_HAS_LCD
    lcd_print_strn(str, len);
    #endif
    mp_uos_dupterm_tx_strn(str, len);
}

// Efficiently convert "\n" to "\r\n"
void mp_hal_stdout_tx_strn_cooked(const char *str, size_t len) {
    const char *last = str;
    while (len--) {
        if (*str == '\n') {
            if (str > last) {
                mp_hal_stdout_tx_strn(last, str - last);
            }
            mp_hal_stdout_tx_strn("\r\n", 2);
            ++str;
            last = str;
        } else {
            ++str;
        }
    }
    if (str > last) {
        mp_hal_stdout_tx_strn(last, str - last);
    }
}

#if __CORTEX_M >= 0x03
void mp_hal_ticks_cpu_enable(void) {
    if (!(DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk)) {
        CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        #if defined(__CORTEX_M) && __CORTEX_M == 7
        // on Cortex-M7 we must unlock the DWT before writing to its registers
        DWT->LAR = 0xc5acce55;
        #endif
        DWT->CYCCNT = 0;
        DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    }
}
#endif

void mp_hal_gpio_clock_enable(GPIO_TypeDef *gpio) {
    #if defined(STM32L476xx) || defined(STM32L496xx)
    if (gpio == GPIOG) {
        // Port G pins 2 thru 15 are powered using VddIO2 on these MCUs.
        HAL_PWREx_EnableVddIO2();
    }
    #endif

    // This logic assumes that all the GPIOx_EN bits are adjacent and ordered in one register

    #if defined(STM32F0)
    #define AHBxENR AHBENR
    #define AHBxENR_GPIOAEN_Pos RCC_AHBENR_GPIOAEN_Pos
    #elif defined(STM32F4) || defined(STM32F7)
    #define AHBxENR AHB1ENR
    #define AHBxENR_GPIOAEN_Pos RCC_AHB1ENR_GPIOAEN_Pos
    #elif defined(STM32H7)
    #define AHBxENR AHB4ENR
    #define AHBxENR_GPIOAEN_Pos RCC_AHB4ENR_GPIOAEN_Pos
    #elif defined(STM32L0)
    #define AHBxENR IOPENR
    #define AHBxENR_GPIOAEN_Pos RCC_IOPENR_IOPAEN_Pos
    #elif defined(STM32L4) || defined(STM32WB)
    #define AHBxENR AHB2ENR
    #define AHBxENR_GPIOAEN_Pos RCC_AHB2ENR_GPIOAEN_Pos
    #endif

    uint32_t gpio_idx = ((uint32_t)gpio - GPIOA_BASE) / (GPIOB_BASE - GPIOA_BASE);
    RCC->AHBxENR |= 1 << (AHBxENR_GPIOAEN_Pos + gpio_idx);
    volatile uint32_t tmp = RCC->AHBxENR; // Delay after enabling clock
    (void)tmp;
}

void mp_hal_pin_config(mp_hal_pin_obj_t pin_obj, uint32_t mode, uint32_t pull, uint32_t alt) {
    GPIO_TypeDef *gpio = pin_obj->gpio;
    uint32_t pin = pin_obj->pin;
    mp_hal_gpio_clock_enable(gpio);
    gpio->MODER = (gpio->MODER & ~(3 << (2 * pin))) | ((mode & 3) << (2 * pin));
    #if defined(GPIO_ASCR_ASC0)
    // The L4 has a special analog switch to connect the GPIO to the ADC
    gpio->OTYPER = (gpio->OTYPER & ~(1 << pin)) | (((mode >> 2) & 1) << pin);
    gpio->ASCR = (gpio->ASCR & ~(1 << pin)) | ((mode >> 3) & 1) << pin;
    #else
    gpio->OTYPER = (gpio->OTYPER & ~(1 << pin)) | ((mode >> 2) << pin);
    #endif
    gpio->OSPEEDR = (gpio->OSPEEDR & ~(3 << (2 * pin))) | (2 << (2 * pin)); // full speed
    gpio->PUPDR = (gpio->PUPDR & ~(3 << (2 * pin))) | (pull << (2 * pin));
    gpio->AFR[pin >> 3] = (gpio->AFR[pin >> 3] & ~(15 << (4 * (pin & 7)))) | (alt << (4 * (pin & 7)));
}

bool mp_hal_pin_config_alt(mp_hal_pin_obj_t pin, uint32_t mode, uint32_t pull, uint8_t fn, uint8_t unit) {
    const pin_af_obj_t *af = pin_find_af(pin, fn, unit);
    if (af == NULL) {
        return false;
    }
    mp_hal_pin_config(pin, mode, pull, af->idx);
    return true;
}

void mp_hal_pin_config_speed(mp_hal_pin_obj_t pin_obj, uint32_t speed) {
    GPIO_TypeDef *gpio = pin_obj->gpio;
    uint32_t pin = pin_obj->pin;
    gpio->OSPEEDR = (gpio->OSPEEDR & ~(3 << (2 * pin))) | (speed << (2 * pin));
}

/*******************************************************************************/
// MAC address

// Generate a random locally administered MAC address (LAA)
void mp_hal_generate_laa_mac(int idx, uint8_t buf[6]) {
    uint8_t *id = (uint8_t *)MP_HAL_UNIQUE_ID_ADDRESS;
    buf[0] = 0x02; // LAA range
    buf[1] = (id[11] << 4) | (id[10] & 0xf);
    buf[2] = (id[9] << 4) | (id[8] & 0xf);
    buf[3] = (id[7] << 4) | (id[6] & 0xf);
    buf[4] = id[2];
    buf[5] = (id[0] << 2) | idx;
}

// A board can override this if needed
MP_WEAK void mp_hal_get_mac(int idx, uint8_t buf[6]) {
    mp_hal_generate_laa_mac(idx, buf);
}

void mp_hal_get_mac_ascii(int idx, size_t chr_off, size_t chr_len, char *dest) {
    static const char hexchr[16] = "0123456789ABCDEF";
    uint8_t mac[6];
    mp_hal_get_mac(idx, mac);
    for (; chr_len; ++chr_off, --chr_len) {
        *dest++ = hexchr[mac[chr_off >> 1] >> (4 * (1 - (chr_off & 1))) & 0xf];
    }
}
