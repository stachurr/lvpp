#include "LvObj.h"



LvObj::LvObj (lv_obj_t* parent /*=nullptr*/)
{
    if (parent == nullptr)
    {
        parent = lv_screen_active();
    }

    m_obj = lv_obj_create(parent);
    lv_obj_null_on_delete(&m_obj);
}

LvObj::~LvObj(void)
{
    if (m_obj)
    {
        lv_obj_delete(m_obj);
    }
}



const LvObj& LvObj::set_size (int32_t w, int32_t h) const
{
    lv_obj_set_size(m_obj, w, h);
    return *this;
}

const LvObj& LvObj::set_style_bg_color (lv_color_t value, lv_style_selector_t selector) const
{
    lv_obj_set_style_bg_color(m_obj, value, selector);
    return *this;
}

const LvObj& LvObj::center(void) const
{
    lv_obj_center(m_obj);
    return *this;
}
