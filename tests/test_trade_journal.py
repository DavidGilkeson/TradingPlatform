"""
Tests for Project Atlas trade calculations.
"""

import pytest

from trade_journal import (
    calculate_trade_result,
)


def test_profitable_long_trade():
    """
    A profitable long trade should return
    positive profit and return.
    """

    profit, return_percent = calculate_trade_result(
        direction="LONG",
        entry_price=100.0,
        exit_price=110.0,
        quantity=10.0,
        fees=5.0,
    )

    assert profit == pytest.approx(95.0)
    assert return_percent == pytest.approx(9.5)


def test_losing_long_trade():
    """
    A losing long trade should return
    a negative result.
    """

    profit, return_percent = calculate_trade_result(
        direction="LONG",
        entry_price=100.0,
        exit_price=90.0,
        quantity=10.0,
        fees=0.0,
    )

    assert profit == pytest.approx(-100.0)

    assert return_percent == pytest.approx(-10.0)


def test_profitable_short_trade():
    """
    A short trade profits when the exit
    price is below the entry price.
    """

    profit, return_percent = calculate_trade_result(
        direction="SHORT",
        entry_price=100.0,
        exit_price=80.0,
        quantity=5.0,
        fees=2.0,
    )

    assert profit == pytest.approx(98.0)

    assert return_percent == pytest.approx(19.6)


def test_break_even_trade_with_fees():
    """
    Fees should make an otherwise
    break-even trade negative.
    """

    profit, return_percent = calculate_trade_result(
        direction="LONG",
        entry_price=100.0,
        exit_price=100.0,
        quantity=10.0,
        fees=10.0,
    )

    assert profit == pytest.approx(-10.0)

    assert return_percent == pytest.approx(-1.0)
