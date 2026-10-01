"""Tools the agent can call. Each takes plain arguments and returns a string for the model.

The functions never raise: a bad call returns "Error: ..." so the model can read it and retry.
"""

import ast
import operator
import re

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

MAX_EXPRESSION_CHARS = 200
# Without these, "9 ** 9 ** 9" would hang the process. Real growth rates need neither.
MAX_EXPONENT = 100
MAX_ABS_VALUE = 1e15  # filing figures are far below this, so a bigger result is a mistake
# The filings print numbers like 4,158,920; the model copies them with the commas.
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_HINT = "Send one plain arithmetic expression, for example (150 - 120) / 120 * 100."


class CalculatorError(ValueError):
    pass


def _eval(node: ast.AST) -> float:
    """Evaluate a parsed expression, accepting only whitelisted node types.

    Anything not listed here (names, calls, attributes, strings, comparisons) is rejected,
    which is why this is safe where eval() is not.
    """
    if isinstance(node, ast.Constant):
        # type() rather than isinstance() so True/False, strings and complex are rejected.
        if type(node.value) in (int, float):
            return node.value
        raise CalculatorError("only plain numbers are allowed")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise CalculatorError(f"exponent larger than {MAX_EXPONENT}")
        try:
            result = _BINARY[type(node.op)](left, right)
        except ZeroDivisionError:
            raise CalculatorError("division by zero") from None
        except OverflowError:
            raise CalculatorError("result too large") from None
        if isinstance(result, complex):  # (-8) ** (1/3) gives a complex number in Python 3
            raise CalculatorError("result is not a real number")
        if abs(result) > MAX_ABS_VALUE:
            raise CalculatorError("result too large")
        return result
    raise CalculatorError("only numbers, + - * / ** and parentheses are allowed")


def _format(value: float) -> str:
    if isinstance(value, int) or value.is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def calculate(expression: str) -> str:
    """Evaluate arithmetic exactly, so the model never does the maths itself."""
    try:
        text = _THOUSANDS.sub("", expression.strip())
        if not text:
            raise CalculatorError("empty expression")
        if len(text) > MAX_EXPRESSION_CHARS:
            raise CalculatorError(f"expression longer than {MAX_EXPRESSION_CHARS} characters")
        return _format(_eval(ast.parse(text, mode="eval").body))
    except CalculatorError as exc:
        return f"Error: {exc}. {_HINT}"
    except (SyntaxError, ValueError, RecursionError):
        return f"Error: could not parse {expression!r}. {_HINT}"
