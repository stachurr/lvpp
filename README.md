# LVPP
C++ binding for LVGL

---

## Items to wrap
| Core          | Misc              | Widgets   |
|---------------|-------------------|-----------|
| lv_display    | lv_anim           | all       |
| lv_event      | lv_anim_timeline  |           |
| lv_indev      | lv_style          |           |
| lv_obj        | lv_timer          |           |
| lv_screen     |                   |           |

#### Issues...
- Initially, it appears that all functions with the prefix `lv_timer_` whose first parameter is `lv_timer_t*` can be public member functions of the `LvTimer` C++ class. But how do we reliably determine constructors? Will they allways contain the word "create", regardless of the object type?
