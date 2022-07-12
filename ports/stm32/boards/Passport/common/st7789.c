#include "st7789.h"

#include <stdio.h>

/* Use STM32 HAL for the bootloader */
#ifdef PASSPORT_BOOTLOADER
#include "stm32h7xx_hal.h"

#define ST7789_RST_Pin GPIO_PIN_8
#define ST7789_RST_GPIO_Port GPIOA
#define ST7789_DC_Pin GPIO_PIN_15
#define ST7789_DC_GPIO_Port GPIOE
#define ST7789_CS_Pin GPIO_PIN_15
#define ST7789_CS_GPIO_Port GPIOA

#define ST7789_SPI_PORT hspi1

static SPI_HandleTypeDef ST7789_SPI_PORT;

/* Basic operations */
#define ST7789_RST_Clr() HAL_GPIO_WritePin(ST7789_RST_GPIO_Port, ST7789_RST_Pin, GPIO_PIN_RESET)
#define ST7789_RST_Set() HAL_GPIO_WritePin(ST7789_RST_GPIO_Port, ST7789_RST_Pin, GPIO_PIN_SET)

#define ST7789_DC_Clr() HAL_GPIO_WritePin(ST7789_DC_GPIO_Port, ST7789_DC_Pin, GPIO_PIN_RESET)
#define ST7789_DC_Set() HAL_GPIO_WritePin(ST7789_DC_GPIO_Port, ST7789_DC_Pin, GPIO_PIN_SET)

#define ST7789_Select() HAL_GPIO_WritePin(ST7789_CS_GPIO_Port, ST7789_CS_Pin, GPIO_PIN_RESET)
#define ST7789_UnSelect() HAL_GPIO_WritePin(ST7789_CS_GPIO_Port, ST7789_CS_Pin, GPIO_PIN_SET)

#define ST7789_DELAY_MS(ms) HAL_Delay(ms)
/**
 * @brief Write command to ST7789 controller
 * @param cmd -> command to write
 * @return none
 */
static void ST7789_WriteCommand(uint8_t cmd) {
    ST7789_Select();
    ST7789_DC_Clr();
    HAL_SPI_Transmit(&ST7789_SPI_PORT, &cmd, sizeof(cmd), HAL_MAX_DELAY);
    ST7789_UnSelect();
}

static void ST7789_WriteData(uint8_t* buff, size_t buff_size) {
    ST7789_Select();
    ST7789_DC_Set();

    // split data in small chunks because HAL can't send more than 64K at once

    while (buff_size > 0) {
        uint16_t chunk_size = buff_size > 65535 ? 65535 : buff_size;
        HAL_SPI_Transmit(&ST7789_SPI_PORT, buff, chunk_size, HAL_MAX_DELAY);
        buff += chunk_size;
        buff_size -= chunk_size;
    }

    ST7789_UnSelect();
}

/**
 * @brief Write data to ST7789 controller, simplified for 8bit data.
 * data -> data to write
 * @return none
 */
static void ST7789_WriteSmallData(uint8_t data) {
    ST7789_Select();
    ST7789_DC_Set();
    HAL_SPI_Transmit(&ST7789_SPI_PORT, &data, sizeof(data), HAL_MAX_DELAY);
    ST7789_UnSelect();
}

/**
 * @brief Initialize the driver for usage on the bootloader.
 */
static void ST7789_HAL_Init(void) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // GPIO Ports Clock Enable
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();

    // Configure GPIO pin Output Level

    // SPI1 GPIO Configuration
    //   PA5     ------> SPI1_SCK
    //   PA7     ------> SPI1_MOSI

    HAL_GPIO_WritePin(GPIOA, ST7789_RST_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, ST7789_CS_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOE, ST7789_DC_Pin, GPIO_PIN_RESET);

    // Configure GPIO pins: PAPin PAPin PAPin
    GPIO_InitStruct.Pin   = ST7789_RST_Pin | ST7789_CS_Pin;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin   = ST7789_DC_Pin;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    // The code below was already here
    GPIO_InitStruct.Pin       = GPIO_PIN_5;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_7;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // Init the SPI bus

    // These configuration values are from the IDE test code (for the Sharp LCD!!!!!)
    ST7789_SPI_PORT.Instance = SPI1;
    SPI_InitTypeDef* init    = &ST7789_SPI_PORT.Init;
    init->Mode               = SPI_MODE_MASTER;
    init->Direction          = SPI_DIRECTION_2LINES;
    init->DataSize           = SPI_DATASIZE_8BIT;
    init->CLKPolarity        = SPI_POLARITY_LOW;
    init->CLKPhase           = SPI_PHASE_1EDGE;
    init->NSS                = SPI_NSS_SOFT;
#ifdef FACTORY_TEST
    // Set lower frequency because factory test fixture LCD wires are too long
    init->BaudRatePrescaler  = SPI_BAUDRATEPRESCALER_4;
#else
    init->BaudRatePrescaler  = SPI_BAUDRATEPRESCALER_2;
#endif
    init->FirstBit           = SPI_FIRSTBIT_MSB;
    init->TIMode             = SPI_TIMODE_DISABLE;
    init->CRCCalculation     = SPI_CRCCALCULATION_DISABLE;
    init->CRCPolynomial      = 10;

    __HAL_RCC_SPI1_CLK_ENABLE();
    HAL_SPI_Init(&ST7789_SPI_PORT);
}
#else /* !defined(PASSPORT_BOOTLOADER) */
/* Use MicroPython STM32 port for the firmware to avoid modifying MicroPython
 * STM32 port IRQ handlers and stuff, also DMA is handled there directly. */

#include "py/mphal.h"
#include "spi.h"
#include "pins.h"

/* maximum timeout in milliseconds */
#define ST7789_SPI_MAX_TIMEOUT (5000)
#define ST7789_SPI_PORT (&spi_obj[0])

#define ST7789_RST_Pin (pin_A8)
#define ST7789_DC_Pin (pin_E15)
#define ST7789_CS_Pin (pin_A15)

/* Basic operations */
#define ST7789_RST_Clr() mp_hal_pin_low(ST7789_RST_Pin)
#define ST7789_RST_Set() mp_hal_pin_high(ST7789_RST_Pin)

#define ST7789_DC_Clr() mp_hal_pin_low(ST7789_DC_Pin)
#define ST7789_DC_Set() mp_hal_pin_high(ST7789_DC_Pin)

#define ST7789_Select() mp_hal_pin_low(ST7789_CS_Pin)
#define ST7789_UnSelect() mp_hal_pin_high(ST7789_CS_Pin)

#define ST7789_DELAY_MS(ms) mp_hal_delay_ms(ms)

/**
 * @brief Write command to ST7789 controller
 * @param cmd -> command to write
 * @return none
 */
static void ST7789_WriteCommand(uint8_t cmd) {
    ST7789_Select();
    ST7789_DC_Clr();
    spi_transfer(ST7789_SPI_PORT, sizeof(cmd), &cmd, NULL, ST7789_SPI_MAX_TIMEOUT);
    ST7789_UnSelect();
}

/**
 * @brief Write data to ST7789 controller
 * @param buff -> pointer of data buffer
 * @param buff_size -> size of the data buffer
 * @return none
 */
static void ST7789_WriteData(uint8_t* buff, size_t buff_size) {
    ST7789_Select();
    ST7789_DC_Set();
    spi_transfer(ST7789_SPI_PORT, buff_size, buff, NULL, ST7789_SPI_MAX_TIMEOUT);
    ST7789_UnSelect();
}

/**
 * @brief Write data to ST7789 controller, simplified for 8bit data.
 * data -> data to write
 * @return none
 */
static void ST7789_WriteSmallData(uint8_t data) {
    ST7789_Select();
    ST7789_DC_Set();
    spi_transfer(ST7789_SPI_PORT, sizeof(data), &data, NULL, ST7789_SPI_MAX_TIMEOUT);
    ST7789_UnSelect();
}

/**
 * @brief Initialize the driver for usage on the firmware.
 */
static void ST7789_HAL_Init(void) {
    // Pin re-initialization doesn't need to be done. It pulls high for a short moment the
    // LCD_RST pin causing the screen to flicker for a short moment.
    //
    // SAFETY:
    // They are already initialized from the bootloader and none of the changes to the clock
    // tree affect the GPIO. So it's safe to use any of the GPIO functions with these pins.

    SPI_InitTypeDef* init = &ST7789_SPI_PORT->spi->Init;
    init->Mode            = SPI_MODE_MASTER;
    init->Direction       = SPI_DIRECTION_2LINES;
    init->DataSize        = SPI_DATASIZE_8BIT;
    init->CLKPolarity     = SPI_POLARITY_LOW;
    init->CLKPhase        = SPI_PHASE_1EDGE;
    init->NSS             = SPI_NSS_SOFT;
    // 125 MHz from pll3_q_ck divided by 2 (62.5 MHz) which is the maximum
    // clock rate (16 clock cycle for writing).
    init->BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
    init->FirstBit          = SPI_FIRSTBIT_MSB;
    init->TIMode            = SPI_TIMODE_DISABLE;
    init->CRCCalculation    = SPI_CRCCALCULATION_DISABLE;
    init->CRCPolynomial     = 10;

    spi_init(ST7789_SPI_PORT, false);
}
#endif /* PASSPORT_BOOTLOADER */

/**
 * @brief Set the rotation direction of the display
 * @param m -> rotation parameter(please refer it in st7789.h)
 * @return none
 */
void ST7789_SetRotation(uint8_t m) {
    ST7789_WriteCommand(ST7789_MADCTL);  // MADCTL
    switch (m) {
        case 0:
            ST7789_WriteSmallData(ST7789_MADCTL_MX | ST7789_MADCTL_MY | ST7789_MADCTL_RGB);
            break;
        case 1:
            ST7789_WriteSmallData(ST7789_MADCTL_MY | ST7789_MADCTL_MV | ST7789_MADCTL_RGB);
            break;
        case 2:
            ST7789_WriteSmallData(ST7789_MADCTL_RGB);
            break;
        case 3:
            ST7789_WriteSmallData(ST7789_MADCTL_MX | ST7789_MADCTL_MV | ST7789_MADCTL_RGB);
            break;
        default:
            break;
    }
}

/**
 * @brief Set address of DisplayWindow
 * @param xi&yi -> coordinates of window
 * @return none
 */
static void ST7789_SetAddressWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
    ST7789_Select();
    uint16_t x_start = x0 + X_SHIFT, x_end = x1 + X_SHIFT;
    uint16_t y_start = y0 + Y_SHIFT, y_end = y1 + Y_SHIFT;

    /* Column Address set */
    ST7789_WriteCommand(ST7789_CASET);
    {
        uint8_t data[] = {x_start >> 8, x_start & 0xFF, x_end >> 8, x_end & 0xFF};
        ST7789_WriteData(data, sizeof(data));
    }

    /* Row Address set */
    ST7789_WriteCommand(ST7789_RASET);
    {
        uint8_t data[] = {y_start >> 8, y_start & 0xFF, y_end >> 8, y_end & 0xFF};
        ST7789_WriteData(data, sizeof(data));
    }
    /* Write to RAM */
    ST7789_WriteCommand(ST7789_RAMWR);
    ST7789_UnSelect();
}

/**
 * @brief Initialize ST7789 controller
 * @param none
 * @return none
 */
void ST7789_Init(bool clear) {
    ST7789_HAL_Init();

#if PASSPORT_BOOTLOADER
    HAL_Delay(25);
    ST7789_RST_Clr();
    HAL_Delay(25);
    ST7789_RST_Set();
    HAL_Delay(50);

    ST7789_WriteCommand(ST7789_COLMOD);  //	Set color mode
    ST7789_WriteSmallData(ST7789_COLOR_MODE_16bit);
    ST7789_WriteCommand(0xB2);  //	Porch control
    {
        uint8_t data[] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
        ST7789_WriteData(data, sizeof(data));
    }
    ST7789_SetRotation(ST7789_ROTATION);  //	MADCTL (Display Rotation)

    // Internal LCD Voltage generator settings
    ST7789_WriteCommand(0XB7);    //	Gate Control
    ST7789_WriteSmallData(0x35);  //	Default value
    ST7789_WriteCommand(0xBB);    //	VCOM setting
    ST7789_WriteSmallData(0x19);  //	0.725v (default 0.75v for 0x20)
    ST7789_WriteCommand(0xC0);    //	LCMCTRL
    ST7789_WriteSmallData(0x2C);  //	Default value
    ST7789_WriteCommand(0xC2);    //	VDV and VRH command Enable
    ST7789_WriteSmallData(0x01);  //	Default value
    ST7789_WriteCommand(0xC3);    //	VRH set
    ST7789_WriteSmallData(0x12);  //	+-4.45v (defalut +-4.1v for 0x0B)
    ST7789_WriteCommand(0xC4);    //	VDV set
    ST7789_WriteSmallData(0x20);  //	Default value
    ST7789_WriteCommand(0xC6);    //	Frame rate control in normal mode
    ST7789_WriteSmallData(0x0F);  //	Default value (60HZ)
    ST7789_WriteCommand(0xD0);    //	Power control
    ST7789_WriteSmallData(0xA4);  //	Default value
    ST7789_WriteSmallData(0xA1);  //	Default value

    ST7789_WriteCommand(ST7789_TEON);  // Tearing Effect output line on
    ST7789_WriteSmallData(0x00);       // V-blanking information only on TE line.

    ST7789_WriteCommand(0xE0);
    {
        // From Daixian
        // Quite a bit brighter!
        // uint8_t data[] = {0xD0, 0x08, 0x0E, 0x09, 0x09, 0x05, 0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34};

        // http://vision.ime.usp.br/~cejnog/librealsense/ubuntu-xenial/drivers/staging/fbtft/fb_st7789v.c
        // Complete mess
        // uint8_t data[] = {0x70, 0x2C, 0x2E, 0x15, 0x10, 0x09, 0x48, 0x33, 0x53, 0x0B, 0x19, 0x18, 0x20, 0x25};

        // https://github.com/crystalfontz/CFAF240320K1-024T-RT/blob/master/CFAF240320K1024TRT_Demo_Code.ino
        // Still pretty dark
        // uint8_t data[] = {0xF0, 0x00, 0x0A, 0x10, 0x12, 0x1B, 0x39, 0x44, 0x47, 0x28, 0x12, 0x10, 0x16, 0x1B};

        // https://github.com/torvalds/linux/blob/master/drivers/staging/fbtft/fb_st7789v.c
        uint8_t data[] = {0xD0, 0x05, 0x0A, 0x09, 0x08, 0x05, 0x2E, 0x44, 0x45, 0x0F, 0x17, 0x16, 0x2B, 0x32};

        ST7789_WriteData(data, sizeof(data));
    }

    ST7789_WriteCommand(0xE1);
    {
        // From Daixian
        // uint8_t data[] = {0xD0, 0x08, 0x0E, 0x09, 0x09, 0x15, 0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34};

        // http://vision.ime.usp.br/~cejnog/librealsense/ubuntu-xenial/drivers/staging/fbtft/fb_st7789v.c
        // uint8_t data[] = {0x70, 0x2C, 0x2E, 0x15, 0x10, 0x09, 0x48, 0x33, 0x53, 0x0B, 0x19, 0x18, 0x20, 0x25};

        // https://github.com/crystalfontz/CFAF240320K1-024T-RT/blob/master/CFAF240320K1024TRT_Demo_Code.ino
        // uint8_t data[] = {0xF0, 0x00, 0x0A, 0x10, 0x11, 0x1A, 0x3B, 0x34, 0x4E, 0x3A, 0x17, 0x16, 0x21, 0x22};

        // https://github.com/torvalds/linux/blob/master/drivers/staging/fbtft/fb_st7789v.c
        uint8_t data[] = {0xD0, 0x05, 0x0A, 0x09, 0x08, 0x05, 0x2E, 0x43, 0x45, 0x0F, 0x16, 0x16, 0x2B, 0x32};

        ST7789_WriteData(data, sizeof(data));
    }

    if (clear) {
        ST7789_Clear(BLACK);
    }

    ST7789_WriteCommand(ST7789_INVON);   //	Inversion ON
    ST7789_WriteCommand(ST7789_SLPOUT);  //	Out of sleep mode
    ST7789_WriteCommand(ST7789_NORON);   //	Normal Display on
    ST7789_WriteCommand(ST7789_DISPON);  //	Main screen turned on
#endif
}

/**
 * @brief Fill the rectangle on the display with the given data
 * @param x
 * @param y
 * @param w
 * @param h
 * @param data
 * @return none
 */
void ST7789_Update_Rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* data) {
    ST7789_SetAddressWindow(x, y, x + w - 1, y + h - 1);
    ST7789_Select();
    ST7789_WriteData(data, w * h * sizeof(uint16_t));
    ST7789_UnSelect();
}

void ST7789_Clear(uint16_t color) {
    // 480 bytes on the stack!
    uint16_t line[ST7789_WIDTH];
    color = (color >> 8) | ((color & 0xFF) << 8);
    for (uint16_t x = 0; x < ST7789_WIDTH; x++) {
        line[x] = color;
    }

    // Update is immediate in firmware
    for (uint16_t y = 0; y < ST7789_HEIGHT; y++) {
        ST7789_Update_Rect(0, y, ST7789_WIDTH, 1, (uint8_t*)line);
    }
}
