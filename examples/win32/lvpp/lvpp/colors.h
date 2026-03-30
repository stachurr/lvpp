#pragma once

 /*======================*
  *   ANSI DEFINITIONS   *
  *======================*/

// Common
#define _ANSI_ESC               "\x1b"
#define _ANSI_CSI               _ANSI_ESC "["

// Select Graphic Rendition (SGR)
#define _ANSI_SGR(args)         _ANSI_CSI #args "m"
#define _ANSI_SGR_RESET         _ANSI_SGR(0)
#define _ANSI_SGR_ITALIC        _ANSI_SGR(3)
#define _ANSI_SGR_NOT_ITALIC    _ANSI_SGR(23)
#define _ANSI_SGR_GRAY          _ANSI_SGR(90)
#define _ANSI_SGR_RED           _ANSI_SGR(91)
#define _ANSI_SGR_GREEN         _ANSI_SGR(92)
#define _ANSI_SGR_YELLOW        _ANSI_SGR(93)
#define _ANSI_SGR_BLUE          _ANSI_SGR(94)
#define _ANSI_SGR_MAGENTA       _ANSI_SGR(95)
#define _ANSI_SGR_CYAN          _ANSI_SGR(96)
#define _ANSI_SGR_RGB(r,g,b)    _ANSI_SGR(38;2;r;g;b)


/*======================*
 *    TEXT ATTRIBUTES   *
 *======================*/

// Weight
#define ANSI_ITALIC(csl)    _ANSI_SGR_ITALIC csl _ANSI_SGR_NOT_ITALIC

// Standard Colors
#define ANSI_GRAY(csl)      _ANSI_SGR_GRAY csl _ANSI_SGR_RESET
#define ANSI_RED(csl)       _ANSI_SGR_RED csl _ANSI_SGR_RESET
#define ANSI_GREEN(csl)     _ANSI_SGR_GREEN csl _ANSI_SGR_RESET
#define ANSI_YELLOW(csl)    _ANSI_SGR_YELLOW csl _ANSI_SGR_RESET
#define ANSI_BLUE(csl)      _ANSI_SGR_BLUE csl _ANSI_SGR_RESET
#define ANSI_MAGENTA(csl)   _ANSI_SGR_MAGENTA csl _ANSI_SGR_RESET
#define ANSI_CYAN(csl)      _ANSI_SGR_CYAN csl _ANSI_SGR_RESET

// 256-bit Colors
#define ANSI_RGB(csl,r,g,b) _ANSI_SGR_RGB(r,g,b) csl _ANSI_SGR_RESET
#define ANSI_PINK(csl)      ANSI_RGB(csl, 255, 50, 200)

