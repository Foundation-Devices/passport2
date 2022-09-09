/**
 * @file lv_qrcode.c
 *
 */

/*********************
 *      INCLUDES
 *********************/
#include "lv_qrcode.h"
#if LV_USE_QRCODE

#include "qrcodegen.h"

/*********************
 *      DEFINES
 *********************/
#define MY_CLASS &lv_qrcode_class

/**********************
 *      TYPEDEFS
 **********************/

/**********************
 *  STATIC PROTOTYPES
 **********************/
static void lv_qrcode_constructor(const lv_obj_class_t * class_p, lv_obj_t * obj);
static void lv_qrcode_destructor(const lv_obj_class_t * class_p, lv_obj_t * obj);

/**********************
 *  STATIC VARIABLES
 **********************/

const lv_obj_class_t lv_qrcode_class = {
    .constructor_cb = lv_qrcode_constructor,
    .destructor_cb = lv_qrcode_destructor,
    .instance_size = sizeof(lv_qrcode_t),
    .base_class = &lv_canvas_class
};

/**********************
 *      MACROS
 **********************/

/**********************
 *   GLOBAL FUNCTIONS
 **********************/

lv_obj_t * lv_qrcode_create(lv_obj_t * parent)
{
    LV_LOG_INFO("begin");
    lv_obj_t * obj = lv_obj_class_create_obj(MY_CLASS, parent);
    lv_obj_class_init_obj(obj);
    return obj;
}


void lv_qrcode_set_buffer(lv_obj_t * obj, void * img_buf, lv_coord_t hor_res, lv_coord_t ver_res, void * modules_buf,
                          int32_t max_version, lv_color_t dark_color, lv_color_t light_color)
{
    lv_qrcode_t * qrcode = (lv_qrcode_t *)obj;

    qrcode->modules_buf = modules_buf;
    qrcode->max_version = max_version;

    // printf("modules buf %p\n", qrcode->modules_buf);

    lv_canvas_set_buffer(obj, img_buf, hor_res, ver_res, LV_IMG_CF_INDEXED_1BIT);
    lv_canvas_set_palette(obj, 0, dark_color);
    lv_canvas_set_palette(obj, 1, light_color);

    lv_color_t c;
    c.full = 1;
    c.full = 1;
    lv_canvas_fill_bg(obj, c, LV_OPA_COVER);
    lv_canvas_fill_bg(obj, c, LV_OPA_COVER);
}

void lv_qrcode_reset_last_version(lv_obj_t * obj)
{
    lv_qrcode_t * qrcode = (lv_qrcode_t *)obj;
    qrcode->last_version = 1;
}

int32_t lv_qrcode_get_last_version(lv_obj_t * obj)
{
    return ((lv_qrcode_t *)obj)->last_version;
}

int32_t lv_qrcode_get_min_fit_version(lv_obj_t * obj, uint32_t data_len)
{
    LV_UNUSED(obj);
    return qrcodegen_getMinFitVersion(qrcodegen_Ecc_LOW, data_len);
}

lv_res_t lv_qrcode_update(lv_obj_t * obj, const void * data, uint32_t data_len, int32_t min_version)
{
    lv_qrcode_t * qrcode = (lv_qrcode_t *)obj;

    lv_color_t c;
    c.full = 1;
    lv_canvas_fill_bg(obj, c, LV_OPA_COVER);

    if(min_version > qrcode->max_version) return LV_RES_INV;

    lv_img_dsc_t * imgdsc = lv_canvas_get_img(obj);
    lv_coord_t res = LV_MIN(imgdsc->header.w, imgdsc->header.h);

    int32_t qr_version = qrcodegen_getMinFitVersion(qrcodegen_Ecc_LOW, data_len);
    if(qr_version <= 0) return LV_RES_INV;
    if(qr_version > qrcode->max_version) return LV_RES_INV;
    if(qr_version < min_version) qr_version = min_version;
    int32_t qr_size = qrcodegen_version2size(qr_version);
    if(qr_size <= 0) return LV_RES_INV;
    int32_t scale = res / qr_size;
    if(scale <= 0) return LV_RES_INV;
    int32_t remain = res % qr_size;

    /* The qr version is incremented by four point */
    uint32_t version_extend = remain / (scale << 2);
    if(version_extend && qr_version < qrcodegen_VERSION_MAX) {
        qr_version = qr_version + version_extend > qrcode->max_version ?
                     qrcode->max_version : qr_version + version_extend;
    }
    qrcode->last_version = qr_version;

    if (data_len > sizeof(qrcode->data_and_tmp)) {
        return LV_RES_INV;
    }

    lv_memcpy(qrcode->data_and_tmp, data, data_len);

    bool ok = qrcodegen_encodeBinary(qrcode->data_and_tmp, data_len,
                                     qrcode->modules_buf, qrcodegen_Ecc_LOW,
                                     qr_version, qr_version,
                                     qrcodegen_Mask_AUTO, true);
    if (!ok) {
        return LV_RES_INV;
    }

    qr_size = qrcodegen_getSize(qrcode->modules_buf);
    scale = res / qr_size;
    int scaled = qr_size * scale;
    int y_margin = (imgdsc->header.h - scaled) / 2;
    int x_margin = (imgdsc->header.w - scaled) / 2;
    uint8_t * buf_u8 = (uint8_t *)imgdsc->data + 8;    /*+8 skip the palette*/

    /* Copy the qr code canvas:
     * A simple `lv_canvas_set_px` would work but it's slow for so many pixels.
     * So buffer 1 byte (8 px) from the qr code and set it in the canvas image */
    uint32_t row_byte_cnt = (imgdsc->header.w + 7) >> 3;
    int y;
    for(y = y_margin; y < scaled + y_margin; y += scale) {
        uint8_t b = 0;
        uint8_t p = 0;
        bool aligned = false;
        int x;
        for(x = x_margin; x < scaled + x_margin; x++) {
            bool a = qrcodegen_getModule(qrcode->modules_buf, (x - x_margin) / scale, (y - y_margin) / scale);

            if(aligned == false && (x & 0x7) == 0) aligned = true;

            if(aligned == false) {
                c.full = a ? 0 : 1;
                lv_canvas_set_px_color(obj, x, y, c);
            }
            else {
                if(!a) b |= (1 << (7 - p));
                p++;
                if(p == 8) {
                    uint32_t px = row_byte_cnt * y + (x >> 3);
                    buf_u8[px] = b;
                    b = 0;
                    p = 0;
                }
            }
        }

        /*Process the last byte of the row*/
        if(p) {
            /*Make the rest of the bits white*/
            b |= (1 << (8 - p)) - 1;

            uint32_t px = row_byte_cnt * y + (x >> 3);
            buf_u8[px] = b;
        }

        /*The Qr is probably scaled so simply to the repeated rows*/
        int s;
        const uint8_t * row_ori = buf_u8 + row_byte_cnt * y;
        for(s = 1; s < scale; s++) {
            lv_memcpy((uint8_t *)buf_u8 + row_byte_cnt * (y + s), row_ori, row_byte_cnt);
        }
    }

    return LV_RES_OK;
}


void lv_qrcode_delete(lv_obj_t * qrcode)
{
    lv_obj_del(qrcode);
}

/**********************
 *   STATIC FUNCTIONS
 **********************/

static void lv_qrcode_constructor(const lv_obj_class_t * class_p, lv_obj_t * obj)
{
    LV_UNUSED(class_p);

    lv_qrcode_t  * qrcode = (lv_qrcode_t *)obj;
    qrcode->modules_buf = NULL;
    qrcode->max_version = 0;
    qrcode->last_version = 0;
}

static void lv_qrcode_destructor(const lv_obj_class_t * class_p, lv_obj_t * obj)
{
    LV_UNUSED(class_p);

    lv_img_dsc_t * img = lv_canvas_get_img(obj);
    lv_img_cache_invalidate_src(img);
}

#endif /*LV_USE_QRCODE*/
