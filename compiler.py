import ast
from collections import defaultdict

class PyxParser(ast.NodeVisitor):
    def __init__(self):
        # list of top-level function names (components)
        self.functions = []
        # map: function_name -> list of use_state call strings
        self.use_state_by_function = defaultdict(list)
        # stack to track current function context (handles nested functions too)
        self._func_stack = []

    def visit_FunctionDef(self, node):
        # push current function name to stack
        self._func_stack.append(node.name)
        # record it as a top-level function if stack depth is 1 (optional)
        if len(self._func_stack) == 1:
            self.functions.append(node.name)
        # visit children (body)
        self.generic_visit(node)
        # pop the function on exit
        self._func_stack.pop()

    def visit_Call(self, node):
        # check if it's a simple use_state(...) call
        # also handles attribute access like hooks.use_state(...) if needed
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # e.g. hooks.use_state
            func_name = node.func.attr

        if func_name == "use_state":
            call_repr = ast.unparse(node)  # readable source form
            current_function = self._func_stack[-1] if self._func_stack else "<module>"
            self.use_state_by_function[current_function].append(call_repr)

        # continue walking
        self.generic_visit(node)

def parse_pyx_file(path):
    with open(path, "r") as f:
        source = f.read()

    tree = ast.parse(source)
    parser = PyxParser()
    parser.visit(tree)

    return parser.functions, dict(parser.use_state_by_function)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python compiler.py <path_to_pyx_file>")
        sys.exit(1)

    functions, use_state_by_function = parse_pyx_file(sys.argv[1])
    print("Top-level functions:", functions)
    print("use_state calls by function:")
    for func, calls in use_state_by_function.items():
        print(f"  {func}:")
        for call in calls:
            print(f"    {call}")
    
    print(use_state_by_function)

