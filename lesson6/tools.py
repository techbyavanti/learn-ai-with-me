"""The tools that the agent can use: search the documents, and calculate."""

import ast
import operator

# Only these operations are allowed. There are no names and no function calls,
# so the model cannot run code on your computer.
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression):
    """Calculate a math expression with + - * / and brackets, for example '30 * 12 * 0.5'."""

    def value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](value(node.left), value(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](value(node.operand))
        raise ValueError("Only numbers, + - * / and brackets are allowed.")

    expression = str(expression).replace("x", "*").replace("×", "*").replace(",", "")
    if len(expression) > 100:
        raise ValueError("The expression is too long.")
    result = value(ast.parse(expression, mode="eval").body)
    return round(result, 2) if isinstance(result, float) else result


def format_number(n):
    """30.0 -> '30', 12.5 -> '12.5'."""
    return str(int(n)) if float(n).is_integer() else str(n)


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the help guide. Returns the 3 closest sections. "
                           "Search again with other words if the result does not answer the question.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "What to look for"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a math expression with numbers, + - * / and brackets. "
                           "Use it for every calculation.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "For example: 30 * 12 * 0.5"}},
                "required": ["expression"],
            },
        },
    },
]
