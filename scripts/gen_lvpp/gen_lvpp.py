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




def get_type_as_str(node):
    type_str = ""
    # is_const = False
    quals = ""

    while True:
        if isinstance(node, c_ast.IdentifierType):
            if len(node.names) != 1:
                raise Exception("unexpected number of names (expected 1): {}".format(",".join(node.names)))
            type_str = node.names[0] + type_str
            # if is_const:
            #     type_str = "const " + type_str
            if quals:
                type_str = " ".join(quals) + " " + type_str
            break
        elif isinstance(node, c_ast.TypeDecl):
            # if len(node.quals) > 1:
            #     raise Exception("unexpected number of qualifiers (expected 1): {}".format(",".join(node.quals)))
            # if len(node.quals) == 1 and node.quals[0] == "const":
            #     is_const = True
            quals = node.quals
        elif isinstance(node, c_ast.PtrDecl):
            if len(type_str) > 0 and type_str[-1] != "*":
                type_str += " "
            type_str += "*"
            if len(node.quals):
                type_str += " ".join(node.quals)
        elif isinstance(node, c_ast.ArrayDecl):
            type_str += "[]"
        
        try:
            node = node.type
        except AttributeError as e:
            raise Exception("Could not determine type")
    return type_str



def get_FuncDecl_name(node: c_ast.FuncDecl) -> str:
    if not isinstance(node, c_ast.FuncDecl):
        raise TypeError("node must be a FuncDecl")

    while not isinstance(node.type, c_ast.TypeDecl):
        node = node.type
    
    return node.type.declname

# def get_FuncDecl_return_type(node: c_ast.FuncDecl):
#     if not isinstance(node, c_ast.FuncDecl):
#         raise TypeError("node must be a FuncDecl")
#
#     type_str = ""
#     while not isinstance(node.type, c_ast.TypeDecl):
#         if isinstance(node.type, c_ast.PtrDecl):
#             type_str += "*"
#         elif isinstance(node.type, c_ast.ArrayDecl):
#             type_str += "[]"
#         else:
#             raise TypeError("unexpected node type: {}".format(type(node.type)))
#         node = node.type
#
#     if
#
#     type_str = node.type.names[0] + type_str

def get_FuncDecl_params(node: c_ast.FuncDecl):
    if not isinstance(node, c_ast.FuncDecl):
        raise TypeError("node must be a FuncDecl")
    if not isinstance(node.args, c_ast.ParamList):
        raise TypeError("node.args must be a ParamList")

    for p in node.args.params:
        type_str = ""
        while True:
            if isinstance(p.type, c_ast.PtrDecl):
                type_str += "*"
            elif isinstance(p.type, c_ast.ArrayDecl):
                type_str += "[]"
            elif isinstance(p.type, c_ast.TypeDecl):
                break
            else:
                raise TypeError("unexpected node type: {}".format(type(p.type)))
            p = p.type
        
        if not isinstance(p.type.type, c_ast.IdentifierType):
            raise TypeError("must be an IdentifierType")

        name = p.type.declname

        identifier = p.type.type
        if len(identifier.names) != 1:
            raise Exception("unexpected number of names: {}".format(len(identifier.names)))
        
        name = identifier.names[0]
    


    


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
    


def pretty_print_FuncDecl(node: c_ast.FuncDecl):
    if not isinstance(node, c_ast.FuncDecl):
        raise TypeError("node must be a FuncDecl")
    
    func_name = _MyFuncDeclVisitor._get_func_name(node)

    pretty = colors.yellow(func_name)
    pretty += "("
    for p in get_funcDecl_params(node):
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


"""
EXAMPLE
****************************************************
FuncDecl(args=ParamList(params=[Decl(name='obj',
                                     quals=['const'
                                           ],
                                     align=[
                                           ],
                                     storage=[
                                             ],
                                     funcspec=[
                                              ],
                                     type=PtrDecl(quals=[
                                                        ],
                                                  type=TypeDecl(declname='obj',
                                                                quals=['const'
                                                                      ],
                                                                align=None,
                                                                type=IdentifierType(names=['lv_obj_t'
                                                                                          ]
                                                                                    )
                                                                )
                                                  ),
                                     init=None,
                                     bitsize=None
                                     )
                               ]
                        ),
         type=TypeDecl(declname='lv_obj_get_child_count',
                       quals=[
                             ],
                       align=None,
                       type=IdentifierType(names=['uint32_t'
                                                 ]
                                           )
                       )
         )
"""


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
        
        func_name = get_FuncDecl_name(node)
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
        """
        We use visit_Decl instead of visit_FuncDecl beacuse the latter
        also catches typedef'd callback signatures.
        """
        if not isinstance(node, c_ast.Decl):
            raise TypeError("Somehow a non-Decl was visited")
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

    # files = collect_h_file_paths(os.path.join("lvgl", "src"))

    # with open("files.txt", "w") as f:
    #     for path in v._files:
    #         f.write(path)
    #         f.write("\n")
    # quit()
    with open("files.txt", "r") as f:
        files = [path[:-1] for path in f.readlines()]

    decls = v.find(files)
    print(len(decls.items()))

    v._print_findings_summary()
    # if WRITE_FINDINGS_TO_FILE:
    #     v._write_findings("findings.txt")

    # def _get_name(n):
    #     while not isinstance(n, c_ast.TypeDecl):
    #         n = n.type
    #     return n.declname
    # for name in sorted([_get_name(decl) for decl in v._decls["lv_display_"]]):
    #     print(name)


    # for prefix,decls in v.items():
    #     if prefix == "lv_obj_":
    #         for d in decls:
    #             # print(d.name, get_funcDecl_params(d.type))
    #             pretty_print_FuncDecl(d)



if __name__ == "__main__":
    setup_env()
    main()
