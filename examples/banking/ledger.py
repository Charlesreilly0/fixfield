"""
Ledger operations for the banking example.

These functions demonstrate fixfield arithmetic in a realistic setting:
  - deposit / withdraw use FixedDecimal arithmetic with automatic rounding
  - apply_interest shows multiplication with precision carried from balance
  - transfer moves money between two accounts atomically
"""
from examples.banking.models import Account, Transaction


_next_tx_id = 1


def _new_tx_id() -> int:
    global _next_tx_id
    tx_id = _next_tx_id
    _next_tx_id += 1
    return tx_id


def deposit(account: Account, amount: str | float, memo: str = "") -> Transaction:
    """Credit ``amount`` to ``account``. Returns the resulting Transaction."""
    tx = Transaction(
        account_id=str(account.account_id),
        amount=amount,
        memo=memo,
    )
    account.balance = account.balance + tx.amount
    return tx


def withdraw(account: Account, amount: str | float, memo: str = "") -> Transaction:
    """
    Debit ``amount`` from ``account``.

    Raises ``FieldOverflowError`` if the account balance would exceed the
    field's digit cap (shouldn't happen in normal use but demonstrates
    the overflow protection).

    The caller is responsible for enforcing any overdraft policy.
    """
    tx = Transaction(
        account_id=str(account.account_id),
        amount=f"-{amount}",
        memo=memo,
    )
    account.balance = account.balance + tx.amount
    return tx


def apply_interest(account: Account) -> None:
    """
    Apply one period's interest to ``account.balance``.

    interest = balance × rate, rounded to the balance field's precision
    (left-operand convention — balance governs the result).
    """
    interest = account.balance * account.rate
    account.balance = account.balance + interest


def transfer(
    source: Account,
    target: Account,
    amount: str | float,
) -> tuple[Transaction, Transaction]:
    """
    Move ``amount`` from ``source`` to ``target``.
    Returns (debit_tx, credit_tx).
    """
    debit  = withdraw(source, amount)
    credit = deposit(target, amount)
    return debit, credit
