import sys
import argparse
import yaml
from lark import Lark, Transformer, exceptions

grammar = r"""
    start: statement*
    statement: constant_decl
    constant_decl: "set" NAME "=" value
    value: array | string | number | expression | name_ref
    array: "(list" value* ")"
    string: /@"([^"]*)"/
    number: /0[oO][0-7]+/
    NAME: /[_a-zA-Z]+/
    name_ref: NAME
    
    expression: "^" "{" expr_body "}"
    expr_body: (value | operator)*
    
    operator: "+" -> op_plus
            | "-" -> op_minus
            | "*" -> op_mult
            | "/" -> op_div
            | "mod" -> op_mod

    %import common.WS
    %ignore WS
    COMMENT: /%\{(.|\n)*?%\}/
    %ignore COMMENT
"""

class ConfigTransformer(Transformer):
    def __init__(self):
        self.constants = {}

    def start(self, items):
        return self.constants

    def constant_decl(self, items):
        name, value = items
        self.constants[str(name)] = value
        return (name, value)

    def value(self, items):
        return items[0]

    def op_plus(self, items): return "+"
    def op_minus(self, items): return "-"
    def op_mult(self, items): return "*"
    def op_div(self, items): return "/"
    def op_mod(self, items): return "mod"

    def array(self, items):
        return list(items)

    def string(self, items):
        return items[0][2:-1]

    def number(self, items):
        try:
            val = items[0].replace('o', 'o').replace('O', 'o')
            return int(val, 8)
        except ValueError:
            raise ValueError(f"Invalid octal number: {items[0]}")

    def name_ref(self, items):
        name = str(items[0])
        if name in self.constants:
            return self.constants[name]
        else:
            raise ValueError(f"Undefined constant: {name}")

    def expr_body(self, items):
        return items

    def expression(self, items):
        stack = []
        tokens = items[0]
        
        for token in tokens:
            if token in ["+", "-", "*", "/", "mod"]:
                if len(stack) < 2:
                    raise ValueError(f"Not enough operands for operator {token}")
                b = stack.pop()
                a = stack.pop()
                
                if not isinstance(a, int) or not isinstance(b, int):
                     raise TypeError(f"Math operations only supported for integers. Got {a} and {b}")

                if token == "+": stack.append(a + b)
                elif token == "-": stack.append(a - b)
                elif token == "*": stack.append(a * b)
                elif token == "/": stack.append(a // b)
                elif token == "mod": stack.append(a % b)
            else:
                stack.append(token)
        
        if len(stack) != 1:
            raise ValueError(f"Expression error. Stack: {stack}")
        
        return stack[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    args = parser.parse_args()

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)

    try:
        config_parser = Lark(grammar, parser='lalr', transformer=ConfigTransformer())
        result = config_parser.parse(text)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            yaml.dump(result, f, allow_unicode=True, default_flow_style=False)
        print(f"Converted '{args.input_file}' to '{args.output_file}'")
    except Exception as e:
        print(f"Error writing YAML: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()