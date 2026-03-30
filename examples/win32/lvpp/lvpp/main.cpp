/*
*   main.cpp
*   Ryan Stachura
*   03-14-2026
* 
*   Small example of running LVGL on Windows.
* 
*   Make sure the following are defined in lv_conf.h:
*       #define LV_USE_OS LV_OS_WINDOWS
*       #define LV_USE_WINDOWS 1
*/
#ifndef _WIN32
    #error "This example is for Windows"
#endif

#include "lvgl.h"
#include "drivers/windows/lv_windows_context.h" // for custom keypad cb

#include "colors.h"
#include "LvObj.h"

#include <cstdio>
#include <csignal>
#include <chrono>
#include <thread>



static bool g_quit_mainloop = false;


static constexpr int64_t ms_to_int64 (const std::chrono::steady_clock::duration& time)
{
    return std::chrono::duration_cast<std::chrono::milliseconds>(time).count();
}
static void sleep_ms_precise (int64_t ms)
{
    using clock = std::chrono::steady_clock;

    /* The amount of time remaining in milliseconds to start spin-locking.
     * For Windows, 15ms is a good value to balance sleep vs spin-lock.
     */
    constexpr uint32_t ms_spin_lock_grace = 15;
    static clock::time_point beg;

    if (ms <= 0)
    {
        return;
    }

    // Sleep in 1ms intervals (not guaranteed).
    while (ms > ms_spin_lock_grace)
    {
        beg = clock::now();
        std::this_thread::sleep_until(beg + std::chrono::milliseconds(1));

        const clock::duration observed_elapsed = (clock::now() - beg);
        const int64_t ms_observed_elapsed = ms_to_int64(observed_elapsed);

        if (ms_observed_elapsed >= ms)
        {
            if (ms_observed_elapsed > ms)
            {
                LV_LOG_WARN("Slept %ld ms more than intended", ms_observed_elapsed - ms);
            }
            return;
        }

        ms -= ms_observed_elapsed;
    }

    // Spin-lock
    beg = clock::now();
    while (ms > ms_to_int64(clock::now() - beg))
    {}
    return;
}


static void csignal_cb (int signum)
{
    g_quit_mainloop = true;
}
static uint32_t ms_elapsed_cb (void)
{
    // LVGL needs a system tick to know the elapsed time for animations and other tasks.

    using clock = std::chrono::steady_clock;
    static const clock::time_point first_call = clock::now();

    return static_cast<uint32_t>(std::chrono::duration_cast<std::chrono::milliseconds>(clock::now() - first_call).count());
}
static void keypad_read_cb (lv_indev_t* keypad, lv_indev_data_t* data)
{
    // This is a modified version of lv_windows_keypad_driver_read_callback.
    lv_windows_window_context_t* context = lv_windows_get_window_context(lv_windows_get_indev_window_handle(keypad));
    if (!context)
    {
        return;
    }

    lv_windows_keypad_queue_item_t* current = (lv_windows_keypad_queue_item_t*)(lv_ll_get_head(&context->keypad.queue));
    if (current)
    {
        data->key = current->key;
        data->state = current->state;
        //////////////////////////////////////////////////////////////// Modified Area Begin
        if (data->key == 'q' && !g_quit_mainloop)
        {
            LV_LOG_USER("User pressed 'q'. Quitting...");
            g_quit_mainloop = true;
        }
        //////////////////////////////////////////////////////////////// Modified Area End
        lv_ll_remove(&context->keypad.queue, current);
        lv_free(current);

        data->continue_reading = true;
    }
}
static void log_print_cb (lv_log_level_t level, const char* buf)
{
    constexpr const char* log_level_indicators[]
    {
        ANSI_GRAY("TRACE"),
        ANSI_GRAY("INFO"),
        ANSI_YELLOW("WARN"),
        ANSI_RED("ERROR"),
        ANSI_CYAN("USER")
    };

    if (!buf)
    {
        printf("[%s] Log buffer was null\n", log_level_indicators[LV_LOG_LEVEL_ERROR]);
    }
    else if (level < 0 || level >= LV_LOG_LEVEL_NUM)
    {
        printf("[%s] Invalid log level: %d\n", log_level_indicators[LV_LOG_LEVEL_ERROR], level);
    }
    else if (level != LV_LOG_LEVEL_NONE)
    {
        // Don't include the original log level indicator.
        if (*buf == '[')
        {
            while (*buf && *buf++ != ']')
            {}
            while (*buf && (*buf == '\t' || *buf == ' '))
            {
                buf++;
            }
        }

        if (*buf)
        {
            printf("[%s]\t%s", log_level_indicators[level], buf);
        }
    }
}
static uint32_t tick_cb (void) {
    // LVGL needs a system tick to know the elapsed time for animations and other tasks.

    using clock = std::chrono::steady_clock;
    static const clock::time_point first_call = clock::now();

    return static_cast<uint32_t>(std::chrono::duration_cast<std::chrono::milliseconds>(clock::now() - first_call).count());
}


static lv_display_t* init_display (void)
{
    constexpr wchar_t   WINDOW_TITLE[]      = L"LVGL on Windows";
    constexpr int32_t   ZOOM_PERCENTAGE     = 100;
    constexpr bool      ALLOW_DPI_OVERRIDE  = false;
    constexpr bool      SIMULATOR_MODE      = false;
    constexpr int32_t   SCREEN_WIDTH        = 400;
    constexpr int32_t   SCREEN_HEIGHT       = 400;

    lv_display_t* display = lv_windows_create_display(WINDOW_TITLE, SCREEN_WIDTH, SCREEN_HEIGHT, ZOOM_PERCENTAGE, ALLOW_DPI_OVERRIDE, SIMULATOR_MODE);
    if (display)
    {
        constexpr auto BYTES_PER_PIXEL = 3; // LV_COLOR_FORMAT_RGB888 is 3 bytes
        static uint8_t buf[SCREEN_WIDTH * SCREEN_HEIGHT / 10 * BYTES_PER_PIXEL];
        lv_display_set_buffers(display, buf, NULL, sizeof(buf), LV_DISPLAY_RENDER_MODE_PARTIAL);
    }

    return display;
}
static lv_indev_t* init_keypad (lv_display_t* display)
{
    lv_indev_t* keypad = lv_windows_acquire_keypad_indev(display);
    if (keypad)
    {
        lv_indev_set_read_cb(keypad, keypad_read_cb);
    }

    return keypad;
}
static lv_indev_t* init_pointer (lv_display_t * display)
{
    return lv_windows_acquire_pointer_indev(display);
}



int main (void)
{
    int rc = EXIT_SUCCESS;
    lv_display_t* display = nullptr;
    lv_indev_t* keypad = nullptr;
    lv_indev_t* pointer = nullptr;
    LvObj* my_obj = nullptr;


    /* Init LVGL */
    lv_init();
    if (!lv_is_initialized())
    {
        fprintf(stderr, "Failed to initialize LVGL\n");
        rc = EXIT_FAILURE;
        goto done;
    }

    lv_tick_set_cb(ms_elapsed_cb);
    lv_log_register_print_cb(log_print_cb);


    /* Init display and input devices */
    display = init_display();
    if (!display)
    {
        LV_LOG_ERROR("Failed to create display");
        rc = EXIT_FAILURE;
        goto done;
    }
    
    keypad = init_keypad(display);
    if (!keypad)
    {
        LV_LOG_ERROR("Failed to create keypad indev");
        rc = EXIT_FAILURE;
        goto done;
    }
    
    pointer = init_pointer(display);
    if (!pointer)
    {
        LV_LOG_ERROR("Failed to create pointer indev");
        rc = EXIT_FAILURE;
        goto done;
    }
    

    /* Stylize screen and create objects */
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_hex(0xffff00), LV_PART_MAIN);

    my_obj = new LvObj();
    my_obj->set_size(200, 200)
        .set_style_bg_color(lv_color_hex(0x00ffff), LV_PART_MAIN)
        .center();

    {
        lv_obj_t* obj = lv_obj_create(lv_screen_active());
        lv_obj_set_size(obj, 100, 100);
        lv_obj_set_style_bg_color(obj, lv_color_hex(0xff0000), LV_PART_MAIN);
        lv_obj_center(obj);
    }
    {
        lv_obj_t* label = lv_label_create(lv_screen_active());
        lv_label_set_text(label, "Hello, World!");
        lv_obj_center(label);
    }


    /* Main loop */
    while (!g_quit_mainloop)
    {
        const auto time_to_sleep = std::chrono::milliseconds(lv_timer_handler());
        const auto ms = ms_to_int64(time_to_sleep);
        sleep_ms_precise(ms);
    }


    /* Clean up and deinit LVGL */
done:
    if (my_obj)
    {
        LV_LOG_INFO("Deleting my_obj");
        delete my_obj;
    }

    if (pointer)
    {
        LV_LOG_INFO("Deleting pointer indev");
        lv_indev_delete(pointer);
    }
    if (keypad)
    {
        LV_LOG_INFO("Deleting keypad indev");
        lv_indev_delete(keypad);
    }
    if (display)
    {
        LV_LOG_INFO("Deleting display indev");
        lv_display_delete(display);
    }

    lv_deinit();
    return rc;
}
