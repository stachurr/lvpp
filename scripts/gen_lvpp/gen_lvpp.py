import os
import platform

import pycparser
import pycparser.c_ast as c_ast
import pycparser.c_parser as c_parser

from typing import List





def parse_file(filename: str):
    if platform.system() == "Windows":
        return pycparser.parse_file(filename,
                                    use_cpp=True,
                                    cpp_path="C:\\mingw\\w64devkit\\bin\\cpp.exe",
                                    # cpp_args=["-U__GNUC__", "-D_MSC_VER"]
                                    )
    else:
        return pycparser.parse_file(filename,
                                    use_cpp=True)



class FuncDefVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.func_defs: List[c_ast.FuncDef] = []

    def visit_FuncDef(self, node: c_ast.FuncDef):
        self.func_defs.append(node)




def setup_env():
    curdir = os.path.dirname(__file__)
    repodir = os.path.abspath(os.path.join(curdir, "..", ".."))
    os.chdir(repodir)

def main():
    # source = os.path.join("scripts", "gen_lvpp", "c_code_example.c")
    source = os.path.join("lvgl", "src", "core", "lv_group.c")
    ast = parse_file(source)
    # print(ast)

    fdv = FuncDefVisitor()
    fdv.visit(ast)
    print("Found", len(fdv.func_defs), "function definition(s)")
    for node in fdv.func_defs:
        if not isinstance(node.decl, c_ast.Decl):
            raise TypeError("Somehow a non-Decl was set")
        if not isinstance(node.decl.coord, c_parser.Coord):
            raise TypeError("Somehow a non-Coord was set")

        print("  {}, line {}".format(node.decl.name, node.decl.coord.line))




if __name__ == "__main__":
    setup_env()
    main()
