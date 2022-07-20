/**
 * @file lv_qrcode
 *
 */

#ifndef LV_QRCODE_H
#define LV_QRCODE_H

#ifdef __cplusplus
extern "C" {
#endif

/*********************
 *      INCLUDES
 *********************/
#include "../../../lvgl.h"
#if LV_USE_QRCODE

/*********************
 *      DEFINES
 *********************/

/**
 * Calculate buffer size for QR Code buffers.
 *
 * @param size The rectangular size in pixels.
 */
#define LV_QRCODE_IMG_BUF_SIZE(size) LV_CANVAS_BUF_SIZE_INDEXED_1BIT((size), (size))

#define LV_QRCODE_MODULES_BUF_SIZE(max_version) (((((max_version) * 4 + 17) * ((max_version) * 4 + 17) + 7) / 8) + 1)

extern const lv_obj_class_t lv_qrcode_class;

typedef struct {
    lv_canvas_t canvas;
    void * modules_buf;
    int32_t max_version;
    int32_t last_version;
} lv_qrcode_t;

/**********************
 *      TYPEDEFS
 **********************/

/**********************
 * GLOBAL PROTOTYPES
 **********************/

/**
 * Create an empty QR Code object.
 * @param parent point to an object where to create the QR code
 * @param parent pointer to an object where to create the QR code.
 * @return pointer to the created QR code object.
 */
lv_obj_t * lv_qrcode_create(lv_obj_t * parent);

/**
 * Set the buffer for the QR code object.
 * @param obj point to an object where to create the QR code
 * @param buffer Buffer where to render the QR code. The size of the buffer
 * should be calculated by using @ref LV_QRCODE_BUF_SIZE with @p size as the
 * parameter.
 * @param size width and height of the QR code
 * @param dark_color dark color of the QR code
 * @param light_color light color of the QR code
 * @return pointer to the created QR code object
 */
void lv_qrcode_set_buffer(lv_obj_t * obj, void * img_buf, lv_coord_t hor_res, lv_coord_t ver_res, void * modules_buf,
                          int32_t max_version, lv_color_t dark_color, lv_color_t light_color);

void lv_qrcode_reset_last_version(lv_obj_t * obj);

int32_t lv_qrcode_get_last_version(lv_obj_t * obj);

int32_t lv_qrcode_get_min_fit_version(lv_obj_t * obj, uint32_t data_len);
/**
 * Set the data of a QR code object
 * @param qrcode pointer to aQ code object
 * @param data data to display
 * @param data_len length of data in bytes
 * @return LV_RES_OK: if no error; LV_RES_INV: on error
 */
lv_res_t lv_qrcode_update(lv_obj_t * obj, const void * data, uint32_t data_len, int32_t min_version);
/**
 * DEPRECATED: Use normal lv_obj_del instead
 * Delete a QR code object
 * @param qrcode pointer to a QR code object
 */
void lv_qrcode_delete(lv_obj_t * qrcode);

/**********************
 *      MACROS
 **********************/

#endif /*LV_USE_QRCODE*/

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /*LV_QRCODE_H*/
