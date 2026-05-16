import pytest

from src.integrated.server import safe_eval


def test_addition():
    assert safe_eval("2 + 3") == 5


def test_subtraction():
    assert safe_eval("10 - 4") == 6


def test_multiplication():
    assert safe_eval("3 * 4") == 12


def test_division():
    assert safe_eval("10 / 4") == 2.5


def test_floor_division():
    assert safe_eval("10 // 3") == 3


def test_modulo():
    assert safe_eval("10 % 3") == 1


def test_power():
    assert safe_eval("2 ** 8") == 256


def test_complex_expression():
    assert safe_eval("(10 + 2) * 3 - 6 / 2") == 33.0


def test_unary_negation():
    assert safe_eval("-5 + 10") == 5


def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        safe_eval("10 / 0")


def test_unsupported_function_raises():
    with pytest.raises((ValueError, SyntaxError)):
        safe_eval("__import__('os')")


def test_string_in_expression_raises():
    with pytest.raises((ValueError, SyntaxError)):
        safe_eval("'hello' + 'world'")


@pytest.mark.asyncio
async def test_calculate_tool():
    from src.integrated.server import calculate

    result = await calculate("2 + 2")
    assert result["result"] == 4
    assert result["expression"] == "2 + 2"


@pytest.mark.asyncio
async def test_calculate_tool_error():
    from src.integrated.server import calculate

    result = await calculate("10 / 0")
    assert "error" in result
