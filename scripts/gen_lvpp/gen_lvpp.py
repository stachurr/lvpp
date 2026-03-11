import os

import pycparser
import pycparser.c_ast as c_ast
import pycparser.c_parser as c_parser

from typing import List, Set, Dict, Iterable, Callable



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

def collect_h_file_paths(root: str):
    paths: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        c_files = [f for f in filenames if f.endswith(".h")]
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
    



class _LVGLFuncDeclVisitor(c_ast.NodeVisitor):
    """Find all function declarations with the given prefixes, calling
    `callback` for each node. Use `.visit()` to begin collecting."""

    def __init__(self, callback: Callable[[str, c_ast.Decl], None], prefixes: Iterable[str]):
        if not callable(callback):
            raise TypeError("callback must be callable")
        for prefix in prefixes:
            if not isinstance(prefix, str):
                raise TypeError("All prefixes must be strings")
        
        self._callback = callback
        self._prefixes = tuple(reversed(sorted(prefixes))) # Avoid clobbering
        self._uids: Set[int] = set()
    
    def visit_Decl(self, node: c_ast.Decl):
        if not isinstance(node, c_ast.Decl):
            raise TypeError("Somehow a non-Decl was given")
        
        # Only look at FuncDecl types
        if not isinstance(node.type, c_ast.FuncDecl):
            return

        if not isinstance(node.coord, c_parser.Coord):
            raise TypeError("Somehow a non-Coord was given")
        if not isinstance(node.name, str):
            raise TypeError("Somehow a non-str was given for the name")
        
        if not node.coord.file.endswith(".h"):
            raise Exception("Only header files can be parsed by this class")

        # Ignore functions added from private headers
        if node.coord.file.endswith("private.h"):
            return

        for prefix in self._prefixes:
            if node.name.startswith(prefix):
                uid = hash("{}:{}:{}".format(os.path.abspath(node.coord.file), node.coord.line, node.coord.column))
                if uid not in self._uids:
                    self._uids.add(uid)
                    self._callback(prefix, node)


class LVGLFuncDeclFinder:
    def __init__(self, prefixes: Iterable[str]):
        self._visitor = _LVGLFuncDeclVisitor(self._node_found_cb, prefixes)
        self._decls: Dict[str, list[c_ast.Decl]] = dict()
        for prefix in prefixes:
            self._decls[prefix] = list()
    
    def _node_found_cb(self, prefix: str, node: c_ast.Decl):
        self._decls[prefix].append(node)

    def find(self, paths: Iterable[str]):
        for p in paths:
            if p.endswith("private.h"):
                print("\x1b[93mSkipping {}...\x1b[0m".format(p))
                continue
            print("Parsing {}...".format(p))
            try:
                ast = parse_file(p)
            except Exception as e:
                print("\x1b[91m{}\x1b[0m".format(e))
                continue
            self._visitor.visit(ast)
    
    def _print_findings(self):
        for prefix, nodes in self._decls.items():
            print("Found {} {}* function declaration(s)".format(len(nodes), prefix))
    
    def _write_findings(self, filename: str):
        with open(filename, "w") as f:
            for prefix, nodes in self._decls.items():
                f.write("Found {} {}* function declaration(s)\n".format(len(nodes), prefix))
                for node in nodes:
                    fixed_coord = "{}:{}:{}".format(os.path.abspath(node.coord.file), node.coord.line, node.coord.column)
                    f.write("  {} -- {}\n".format(node.name, fixed_coord))
                f.write("\n")





def setup_env():
    """Move to the top-level directory of this repo"""

    curdir = os.path.dirname(__file__)
    repodir = os.path.abspath(os.path.join(curdir, "..", ".."))
    os.chdir(repodir)

def main():
    visitor = MyNodeVisitor()
    paths = collect_h_file_paths("lvgl\\src")

    visitor.parse_files(paths)
    visitor._print_findings()
    if WRITE_FINDINGS_TO_FILE:
        visitor._write_findings("findings.txt")


    


def get_widget_prefixes():
    dir = os.path.join("lvgl", "src", "widgets")
    ignore = ("property", "objx_templ")

    prefixes: List[str] = []
    for dirpath, dirnames, filenames in os.walk(dir):
        for widget_name in dirnames:
            if widget_name not in ignore:
                prefixes.append("lv_{}_".format(widget_name))
    return prefixes

if __name__ == "__main__":
    setup_env()
    # main()



    prefixes = (
        # Core
        "lv_display_",
        "lv_event_",
        "lv_indev_",
        "lv_obj_",
        "lv_screen_",

        # Misc
        "lv_anim_",
        "lv_anim_timeline_",
        "lv_style_",
        "lv_timer_",

        # Widgets
        *get_widget_prefixes()
    )
    v = LVGLFuncDeclFinder(prefixes)
    v.find(collect_h_file_paths("lvgl\\src"))
    v._print_findings()
    v._write_findings("header_findings.txt")
    
