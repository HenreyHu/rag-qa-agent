"""Tools the agent can call. Each takes plain arguments and returns a string for the model.

A bad call returns "Error: ..." so the model can read it and retry. Real faults (for example a
missing Chroma database) still raise, because they are not the model's mistake.
"""

import ast
import operator
import re

from src.config import COMPANIES, find_company, load_filings
from src.retrieve import citation, search

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


# Same k and chunking as the Week 2 baseline, so the comparison changes only the loop and tools.
SEARCH_K = 5


class SearchInputError(ValueError):
    pass


def _available_years() -> dict[str, list[int]]:
    """The fiscal years pinned in data/filings.json, per company short name."""
    years: dict[str, list[int]] = {}
    for filing in load_filings():
        years.setdefault(filing.company.short_name, []).append(filing.fiscal_year)
    return {name: sorted(values) for name, values in years.items()}


def _filters(company, year) -> dict:
    """Validate the optional arguments against the registry. Models sometimes send "" for 'none'."""
    available = _available_years()
    filters: dict = {}
    if company:
        try:
            filters["company"] = find_company(str(company)).short_name
        except KeyError:
            raise SearchInputError(
                f"unknown company {company!r}; choose from {sorted(available)}"
            ) from None
    if year:
        try:
            wanted = int(year)
        except (TypeError, ValueError):
            raise SearchInputError(f"year must be a number such as 2025, got {year!r}") from None
        scope = {name: available[name] for name in [filters["company"]]} if company else available
        if not any(wanted in years for years in scope.values()):
            have = "; ".join(f"{name}: {years}" for name, years in scope.items())
            raise SearchInputError(f"no FY{wanted} report available ({have})")
        filters["year"] = wanted
    return filters


def _scope(filters: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in filters.items()) or "no filters"


def _format_hits(hits: list[dict], query: str, filters: dict) -> str:
    lines = [f"{len(hits)} results for {query!r} ({_scope(filters)})"]
    for rank, hit in enumerate(hits, start=1):
        kind = "table" if hit["is_table"] else "text"
        body = hit["text"].split("\n", 1)[-1]  # the chunk's own header line repeats ours
        lines.append(f"\nResult {rank} {citation(hit)} | {kind} | {hit['section']}\n{body}")
    return "\n".join(lines)


def search_reports(
    query: str, company: str | None = None, year: int | None = None, *, seen: list | None = None
) -> str:
    """Search the annual reports. `seen`, if given, collects the raw hits for the agent's eval."""
    if not isinstance(query, str) or not query.strip():
        return "Error: query is empty. Send the topic or line item to look for."
    try:
        filters = _filters(company, year)
    except SearchInputError as exc:
        return f"Error: {exc}. Fix the arguments and search again."
    hits = search(query.strip(), SEARCH_K, filters)
    if seen is not None:
        seen.extend(hits)
    if not hits:
        return f"No results for {query!r} ({_scope(filters)}). Try different wording."
    return _format_hits(hits, query.strip(), filters)


def tool_schemas() -> list[dict]:
    """The tool definitions sent to Claude, built from the registry so they match the validation."""
    names = ", ".join(c.full_name for c in COMPANIES.values())
    years = sorted({y for values in _available_years().values() for y in values})
    return [
        {
            "name": "search_reports",
            "description": (
                f"Search the annual reports (Form 20-F) of {names}. Returns the top {SEARCH_K} "
                "passages, each headed by its citation [Company, FYyear, p.X]. Make one call per "
                "company and year. Put the topic or line item in the query, and pass the "
                "company and year as arguments, not in the query text. The FY report also shows "
                "the prior year's comparatives."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to look for, e.g. 'total revenue' or 'driver-partner "
                        "classification risk'.",
                    },
                    "company": {
                        "type": "string",
                        "enum": [c.short_name for c in COMPANIES.values()],
                        "description": "Only search this company's reports.",
                    },
                    "year": {
                        "type": "integer",
                        "enum": years,
                        "description": "Fiscal year of the report to search, e.g. 2025 for the "
                        "year ended December 31, 2025.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "calculate",
            "description": (
                "Evaluate an arithmetic expression exactly. Supports + - * / ** and parentheses. "
                "Use it for every growth rate, ratio, difference or sum, e.g. "
                "'(127.4 - 100.5) / 100.5 * 100'. Copy numbers exactly as printed in the results."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The arithmetic expression."}
                },
                "required": ["expression"],
            },
        },
    ]
