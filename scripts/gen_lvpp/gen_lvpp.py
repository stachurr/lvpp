import os

import pycparser
import pycparser.c_ast as c_ast
import pycparser.c_parser as c_parser

from typing import List, Set, Dict, Iterable



# Local path to CPP or GCC.
CPP_PATH = "C:\\mingw\\w64devkit\\bin\\cpp.exe"

# Debug options
WRITE_FINDINGS_TO_FILE = False






def parse_file(filename: str):
    include = os.path.join("scripts", "gen_lvpp", "fake_libc_include")
    return pycparser.parse_file(filename,
                                use_cpp=True,
                                cpp_path=CPP_PATH,
                                cpp_args=["-E",                     # Preprocess only (when using gcc).
                                          "-nostdinc",              # Block inclusion of real standard libraries. We only want our fake stubs.
                                          "-D__attribute__(x)=",    # pycparser does not support GNU __attribute__, so remove all instances.
                                          "-I{}".format(include)    # Provide fake stubs of standard libraries.
                                          ]
                                )

def collect_c_file_paths(root: str):
    paths: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        c_files = [f for f in filenames if f.endswith(".c")]
        for file in c_files:
            paths.append(os.path.join(dirpath, file))
    return paths




class MyNodeVisitor(c_ast.NodeVisitor):
    """Custom NodeVisitor to track relevant LVGL info"""

    def __init__(self):
        self.prefixes = [
            # Core
            "lv_display_",
            "lv_event_",
            "lv_indev_",
            "lv_obj_",
            "lv_screen_",

            # Misc
            "lv_anim_",
            "lv_anim_timeline_", # needs to come before lv_anim_ otherwise these will be consumed
            "lv_style_",
            "lv_timer_",

            # Widgets
            # added at runtime
        ]

        self.func_defs: Dict[str, List[c_ast.FuncDef]] = dict()
        self._ids: Dict[str, Set[str]] = dict()

        self._add_widget_prefixes()

        # Avoid consuming subsets
        self.prefixes = list(reversed(sorted(self.prefixes)))
        print("Prefixes:", self.prefixes)

        # Init values for each key
        for prefix in self.prefixes:
            self.func_defs[prefix] = list()
            self._ids[prefix] = set()
    
    def _add_widget_prefixes(self):
        dir = os.path.join("lvgl", "src", "widgets")
        ignore = ("property", "objx_templ")

        for dirpath, dirnames, filenames in os.walk(dir):
            for widget_name in dirnames:
                if widget_name not in ignore:
                    self.prefixes.append("lv_{}_".format(widget_name))
    
    def _print_findings(self):
        for prefix in self.prefixes:
            print("Found {:3d} {}* function definition(s)\n".format(len(self.func_defs[prefix]), prefix), end="")

    def _write_findings(self, filename: str):
        with open(filename, "w") as file:
            for prefix in self.prefixes:
                if WRITE_FINDINGS_TO_FILE:
                    file.write("Found {:3d} {}* function definition(s)\n".format(len(self.func_defs[prefix]), prefix))
                    for node in self.func_defs[prefix]:
                        id = "{}:{}:{}".format(os.path.abspath(node.coord.file), node.coord.line, node.coord.column)
                        file.write("  {} -- {}\n".format(node.decl.name, id))
                    file.write("\n")

    def parse_files(self, paths: Iterable[str]):
        for p in paths:
            # UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 290995: character maps to <undefined>
            if p.endswith("lv_init.c"):
                print("Skipping {}...".format(p))
                continue

            # Some widgets may not be found without enabling lv_conf.h...
            print("Parsing {}...".format(p))
            ast = parse_file(p)
            self.visit(ast)

    def visit_FuncDef(self, node: c_ast.FuncDef):
        if not isinstance(node.decl, c_ast.Decl):
            raise TypeError("Somehow a non-Decl was set")
        if not isinstance(node.decl.name, str):
            raise TypeError("Somehow a Decl name was not set")
        if not isinstance(node.coord, c_parser.Coord):
            raise TypeError("Somehow a Coord name was not set")
        
        id = "{}:{}:{}".format(os.path.abspath(node.coord.file), node.coord.line, node.coord.column)
        for prefix in self.prefixes:
            if node.decl.name.startswith(prefix):
                if not id in self._ids[prefix]:
                    self._ids[prefix].add(id)
                    self.func_defs[prefix].append(node)
                break






def setup_env():
    """Move to the top-level directory of this repo"""

    curdir = os.path.dirname(__file__)
    repodir = os.path.abspath(os.path.join(curdir, "..", ".."))
    os.chdir(repodir)

def main():
    visitor = MyNodeVisitor()
    paths = collect_c_file_paths("lvgl\\src")

    visitor.parse_files(paths)
    visitor._print_findings()
    if WRITE_FINDINGS_TO_FILE:
        visitor._write_findings("findings.txt")


    




if __name__ == "__main__":
    setup_env()
    main()
