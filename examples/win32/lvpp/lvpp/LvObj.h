#pragma once
#include "lvgl.h"


class LvObj
{
public:
    LvObj (lv_obj_t* parent = nullptr);
    virtual ~LvObj (void);

    const LvObj& set_size (int32_t w, int32_t h) const;
    const LvObj& set_style_bg_color (lv_color_t value, lv_style_selector_t selector) const;
    const LvObj& center (void) const;

private:
    lv_obj_t* m_obj;
};
