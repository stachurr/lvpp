if __name__ == "__main__":
    quit("This file is not a script")





def _make_color(s: str, v: int):
    return "\x1b[{}m{}\x1b[39m".format(v, s)

def _constrain_255(v: int):
    return min(255, max(0, v))



def gray(s: str):
    return _make_color(s, 90)

def red(s: str):
    return _make_color(s, 91)

def green(s: str):
    return _make_color(s, 92)

def yellow(s: str):
    return _make_color(s, 93)

def blue(s: str):
    return _make_color(s, 94)

def magenta(s: str):
    return _make_color(s, 95)

def cyan(s: str):
    return _make_color(s, 96)



def rgb(s: str, r: int, g: int, b: int):
    r = _constrain_255(r)
    g = _constrain_255(g)
    b = _constrain_255(b)
    return _make_color(s, "38;2;{};{};{}".format(r,g,b))

def hex(s: str, hexcode: int):
    b = hexcode & 0xff
    hexcode >>= 8
    g = hexcode & 0xff
    hexcode >>= 8
    r = hexcode & 0xff
    return rgb(s, r, g, b)
