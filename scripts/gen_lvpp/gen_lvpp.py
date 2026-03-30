import os
from typing import List, Set, Dict, Iterable, Callable, Tuple
from dataclasses import dataclass

import pycparser
import pycparser.c_ast as c_ast
import pycparser.c_parser as c_parser

import colors





# Local path to CPP or GCC.
CPP_PATH = "C:\\mingw\\w64devkit\\bin\\cpp.exe"





FUNC_NAME_COLOR = 0xe9c46a
QUALIFIER_COLOR = 0x00296b
POINTER_COLOR   = 0xb5179e
BRACE_COLOR     = 0xf4a261
VAR_NAME_COLOR  = 0x8ecae6
TYPE_COLOR      = 0x0ead69





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





@dataclass
class NodeTypeAndName:
    type_quals:     List[str]
    types:          List[str]
    pointer_quals:  List[List[str]]
    pointers:       List[str]
    array_quals:    List[List[str]]
    arrays:         List[str]
    name:           str
    _node:          c_ast.Node

    @staticmethod
    def from_node(node):
        type_quals:     List[str]       = []
        types:          List[str]       = []
        pointer_quals:  List[List[str]] = []
        pointers:       List[str]       = []
        array_quals:    List[List[str]] = []
        arrays:         List[str]       = []
        name:           str             = ""
        _node:          c_ast.Node      = node

        while True:
            quals = getattr(node, "quals", [])

            if isinstance(node, c_ast.PtrDecl):
                pointers.append("*")
                pointer_quals.append(quals)
            elif isinstance(node, c_ast.ArrayDecl):
                arrays.append("[]")
                array_quals.append(quals)
            elif isinstance(node, c_ast.TypeDecl):
                name = node.declname
                type_quals = quals
            elif isinstance(node, c_ast.IdentifierType):
                types = node.names
                break
            elif isinstance(node, c_ast.Struct):
                break
            elif isinstance(node, c_ast.EllipsisParam):
                name = "..."
                break

            node = node.type

        return NodeTypeAndName(type_quals, types, pointer_quals, pointers, array_quals, arrays, name, _node)
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.formatted()

    def _stringify_type_name(self, colored: bool):
        s = ""

        if self.type_quals:
            temp = " ".join(self.type_quals)
            if colored:
                s += colors.hex(temp + " ", QUALIFIER_COLOR, reset=False)
            else:
                s += temp + " "
        
        temp = " ".join(self.types)
        if colored:
            s += colors.hex(temp, TYPE_COLOR, reset=False)
        else:
            s += temp

        s = s.strip(" ")
        if colored:
            s = colors.reset(s)
        return s

    def _stringify_type_pointers(self, colored: bool):
        s = ""

        for pointer,quals in zip(self.pointers, self.pointer_quals):
            if colored:
                s += colors.hex(pointer, POINTER_COLOR, reset=False)
            else:
                s += pointer
            
            if quals:
                if self.name == "lv_obj_null_on_delete":
                    input("quals = {}".format(quals))
                temp = " " + " ".join(quals) + " "
                if colored:
                    s += colors.hex(temp, QUALIFIER_COLOR, reset=False)
                else:
                    s += temp

        # if self.name == "lv_obj_null_on_delete":
        #     input("BEFORE STRIP: '{}'".format(s))
        
        s = s.strip(" ")

        # if self.name == "lv_obj_null_on_delete":
        #     input("AFTER STRIP: '{}'".format(s))
            
        if colored:
            s = colors.reset(s)
        return s

    def _stringify_name(self, colored: bool):
        s = ""

        if colored:
            if self.is_function():
                s += colors.hex(self.name, FUNC_NAME_COLOR, reset=False)
            else:
                s += colors.hex(self.name, VAR_NAME_COLOR, reset=False)
        else:
            s += self.name
        
        s = s.strip(" ")
        if colored:
            s = colors.reset(s)
        return s

    def _stringify_arrays(self, colored: bool):
        s = ""

        for array,quals in zip(self.arrays, self.array_quals):
            if colored:
                s += colors.hex(array, POINTER_COLOR, reset=False)
            else:
                s += array

            if quals:
                temp = " ".join(quals)
                if colored:
                    s += colors.hex(temp, QUALIFIER_COLOR, reset=False)
                else:
                    s += temp

            s += " "

        s = s.strip(" ")
        if colored:
            s = colors.reset(s)
        return s

    def is_function(self):
        return isinstance(self._node, c_ast.FuncDecl)

    def is_const(self):
        return "const" in self.type_quals
    
    def formatted(self, colored: bool = False):
        return "{}{} {}{}".format(
            self._stringify_type_name(colored),
            self._stringify_type_pointers(colored),
            self._stringify_name(colored),
            self._stringify_arrays(colored)
        )




def get_funcDecl_params(decl: c_ast.FuncDecl):
    if not isinstance(decl, c_ast.FuncDecl):
        raise TypeError("Must be a FuncDecl")
    
    params: List[NodeTypeAndName] = []
    for p in decl.args.params:
        params.append(NodeTypeAndName.from_node(p))
    return params
    
def pretty_print_FuncDecl(node: c_ast.FuncDecl):
    if not isinstance(node, c_ast.FuncDecl):
        raise TypeError("node must be a FuncDecl")
    
    pretty = NodeTypeAndName.from_node(node).formatted(colored=True)
    pretty += colors.hex("(", BRACE_COLOR)
    for p in get_funcDecl_params(node):
        pretty += p.formatted(colored=True)
        pretty += ", "
    if pretty.endswith(", "):
        pretty = pretty.removesuffix(", ")
    pretty += colors.hex(")", BRACE_COLOR)
    print(pretty)



class _MyFuncDeclVisitor(c_ast.NodeVisitor):
    def __init__(self, callback: Callable[[str, c_ast.FuncDecl], None], prefixes: Iterable[str]):
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
        if coord.column:
            col = coord.column
        else:
            col = ""
        return hash("{}{}{}".format(os.path.abspath(coord.file), coord.line, col))

    def _handle_FuncDecl(self, node: c_ast.FuncDecl):
        if not isinstance(node.coord, c_parser.Coord):
            raise TypeError("coord was missing from node")
        if not node.coord.file.endswith(".h"):
            raise Exception("Only header files can be parsed by this class")
        if node.coord.file.endswith("private.h"):
            return # Ignore functions added from private headers
        
        func_name = NodeTypeAndName.from_node(node).name
        for p in self._prefixes:
            if func_name.startswith(p):
                uid = self._hash_coord(node.coord)
                if uid not in self._uids:
                    self._uids.add(uid)
                    self._callback(p, node)
                    # if func_name.endswith("_t"):
                    #     print(node)
                    break

    def visit_Decl(self, node: c_ast.Decl):
        # IMPORTANT:
        # Even though we want to visit FuncDecl's, we need to visit
        # all Decl's otherwise we'd miss typedef'd callback signatures.

        # Possible types of children:
        #   FuncDecl
        #   Struct
        #   TypeDecl
        #   PtrDecl
        #   ArrayDecl
        #   Enum

        if not isinstance(node.type, c_ast.FuncDecl):
            return
        
        self._handle_FuncDecl(node.type)

class MyFuncDeclFinder:
    def __init__(self, prefixes: Iterable[str]):
        self._visitor = _MyFuncDeclVisitor(self._node_found_cb, prefixes)
        self._decls: Dict[str, List[c_ast.FuncDecl]] = dict()
        for p in prefixes:
            self._decls[p] = list()
    
    def _node_found_cb(self, prefix: str, node: c_ast.FuncDecl):
        self._decls[prefix].append(node)

    def _print_findings_summary(self):
        for prefix, nodes in self._decls.items():
            print("Found {} {}* function declaration(s)".format(len(nodes), prefix))

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

        # Return the map from prefix to nodes
        return self._decls





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
    v = MyFuncDeclFinder(prefixes)

    with open("files.txt", "r") as f:
        files = [path[:-1] for path in f.readlines()]

    decl_map = v.find(files)
    for prefix,decls in decl_map.items():
        print("\n{}*:".format(prefix))
        for d in decls:
            pretty_print_FuncDecl(d)

    v._print_findings_summary()



if __name__ == "__main__":
    setup_env()
    main()
