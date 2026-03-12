if __name__ == "__main__":
    quit("This file is not a script")




def red(s: str):
    return "\x1b[91m{}\x1b[0m".format(s)

def yellow(s: str):
    return "\x1b[93m{}\x1b[0m".format(s)
