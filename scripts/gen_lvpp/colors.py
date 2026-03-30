if __name__ == "__main__":
    quit("This file is not a script")





def _make_color(string: str, v: int, *, reset: bool = True):
    string = "\x1b[{}m{}".format(v, string)

    if reset:
        string += "\x1b[39m"

    return string

def _constrain_255(v: int):
    return min(255, max(0, v))



def gray(string: str):
    return _make_color(string, 90)

def red(string: str):
    return _make_color(string, 91)

def green(string: str):
    return _make_color(string, 92)

def yellow(string: str):
    return _make_color(string, 93)

def blue(string: str):
    return _make_color(string, 94)

def magenta(string: str):
    return _make_color(string, 95)

def cyan(string: str):
    return _make_color(string, 96)



def rgb(string: str, r: int, g: int, b: int, *, reset: bool = True):
    r = _constrain_255(r)
    g = _constrain_255(g)
    b = _constrain_255(b)
    return _make_color(string, "38;2;{};{};{}".format(r,g,b), reset=reset)

def hex(string: str, hexcode: int, *, reset: bool = True):
    b = hexcode & 0xff
    hexcode >>= 8
    g = hexcode & 0xff
    hexcode >>= 8
    r = hexcode & 0xff
    return rgb(string, r, g, b, reset=reset)



def reset(string: str):
    return string + "\x1b[0m"
