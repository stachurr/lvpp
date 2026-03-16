import os
from typing import List, Set, Dict, Iterable, Callable, Tuple
from dataclasses import dataclass

import pycparser
import pycparser.c_ast as c_ast
import pycparser.c_parser as c_parser

import colors





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

def get_widget_prefixes():
    dir = os.path.join("lvgl", "src", "widgets")
    ignore = ("property", "objx_templ")

    prefixes: List[str] = []
    for dirpath, dirnames, filenames in os.walk(dir):
        for widget_name in dirnames:
            if widget_name not in ignore:
                prefixes.append("lv_{}_".format(widget_name))
    return tuple(prefixes)




class _LVGLFuncDeclVisitor(c_ast.NodeVisitor):
    """Find all function declarations with the given prefixes, calling
    `callback` for each node.

    The callback parameters are the prefix and node.
    
    Use `.visit()` to begin collecting."""

    def __init__(self, callback: Callable[[str, c_ast.Decl], None], prefixes: Iterable[str]):
        if not callable(callback):
            raise TypeError("callback must be callable")
        for prefix in prefixes:
            if not isinstance(prefix, str):
                raise TypeError("All prefixes must be strings")
        
        self._callback = callback
        self._prefixes = tuple(reversed(sorted(prefixes))) # Avoid clobbering (ex: lv_anim_timeline_* vs lv_anim_*)
        self._uids: Set[int] = set()
    
    @staticmethod
    def _hash_coord(coord: c_parser.Coord):
        return hash("{}{}{}".format(os.path.abspath(coord.file), coord.line, coord.column))

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
                uid = self._hash_coord(node.coord)
                if uid not in self._uids:
                    self._uids.add(uid)
                    self._callback(prefix, node)

class LVGLFuncDeclFinder:
    """desc todo"""

    def __init__(self, prefixes: Iterable[str]):
        self._visitor = _LVGLFuncDeclVisitor(self._node_found_cb, prefixes)
        self._decls: Dict[str, list[c_ast.Decl]] = dict()
        for prefix in prefixes:
            self._decls[prefix] = list()
    
    def _node_found_cb(self, prefix: str, node: c_ast.Decl):
        self._decls[prefix].append(node)

    def find(self, paths: Iterable[str]):
        for p in paths:
            # No need to parse *private.h files
            if p.endswith("private.h"):
                print(colors.yellow("Skipping {}...".format(p)))
                continue

            # Ignore any errors parsing files... for now this works fine
            print("Parsing {}...".format(p))
            try:
                ast = parse_file(p)
            except Exception as e:
                print(colors.red(e))
                continue

            # Collect function declarations
            self._visitor.visit(ast)
    
    def _print_findings_summary(self):
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

    def items(self):
        return self._decls.items()



@dataclass
class LVGLFuncDeclParam:
    is_const: bool
    type: str
    name: str

def get_param_type(node) -> Tuple[bool, str]:
    if isinstance(node, c_ast.PtrDecl):
        is_const,name = get_param_type(node.type)
        return (is_const, name + "*")
    elif isinstance(node, c_ast.ArrayDecl):
        is_const,name = get_param_type(node.type)
        return (is_const, name + "[]")
    elif isinstance(node, c_ast.TypeDecl):
        if len(node.type.names) > 1:
            raise Exception("unexpected number of names")
        is_const = False
        if node.quals:
            if len(node.quals) > 1:
                raise Exception("unexpected number of quals")
            if node.quals[0] == "const":
                is_const = True
        return (is_const, node.type.names[0])
    else:
        raise Exception("unexpected node type")

def get_param_name(node) -> str:
    if isinstance(node, c_ast.PtrDecl):
        return get_param_name(node.type)
    elif isinstance(node, c_ast.ArrayDecl):
        return get_param_name(node.type)
    elif isinstance(node, c_ast.TypeDecl):
        return node.declname
    else:
        raise Exception("unexpected node type")

def get_funcDecl_params(decl: c_ast.FuncDecl):
    if not isinstance(decl, c_ast.FuncDecl):
        raise TypeError("Must be a FuncDecl")
    
    params: List[LVGLFuncDeclParam] = []
    for p in decl.args.params:
        is_const, type = get_param_type(p.type)
        name = get_param_name(p.type)
        params.append(LVGLFuncDeclParam(is_const, type, name))
    return params
    



def pretty_print_FuncDecl(decl: c_ast.Decl):
    if not isinstance(decl, c_ast.Decl):
        raise TypeError("must be a Decl")
    if not isinstance(decl.type, c_ast.FuncDecl):
        raise TypeError("must be a FuncDecl")

    pretty = colors.yellow(decl.name)
    pretty += "("
    for p in get_funcDecl_params(decl.type):
        if p.is_const:
            pretty += colors.magenta("const ")
        if p.type.endswith("*"):
            lhs,rhs = p.type.split("*", maxsplit=1)
            rhs += "*"
            pretty += colors.cyan(lhs)
            pretty += colors.red(rhs)
        elif p.type.endswith("[]"):
            lhs,rhs = p.type.split("[]", maxsplit=1)
            rhs += "[]"
            pretty += colors.cyan(lhs)
            pretty += colors.red(rhs)
        else:
            pretty += colors.cyan(p.type)
        pretty += " "
        pretty += colors.gray(p.name)
        pretty += ", "
    if pretty.endswith(", "):
        pretty = pretty.removesuffix(", ")
    pretty += ")"
    print(pretty)


def setup_env():
    """Move to the top-level directory of this repo"""

    curdir = os.path.dirname(__file__)
    repodir = os.path.abspath(os.path.join(curdir, "..", ".."))
    os.chdir(repodir)

def main():
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
    v.find(collect_h_file_paths(os.path.join("lvgl", "src")))

    # v._print_findings_summary()
    # if WRITE_FINDINGS_TO_FILE:
    #     v._write_findings("findings.txt")

    for prefix,decls in v.items():
        if prefix == "lv_obj_":
            for d in decls:
                # print(d.name, get_funcDecl_params(d.type))
                pretty_print_FuncDecl(d)



if __name__ == "__main__":
    setup_env()
    main()
