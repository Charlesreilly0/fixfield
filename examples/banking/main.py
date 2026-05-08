"""
Banking example — end-to-end demo of fixfield features.

Run with:
    cd /path/to/workbooks
    uv run python -m examples.banking.main
"""
from fixfield import FieldOverflowError
from examples.banking.models import Account, Branch
from examples.banking.ledger import deposit, withdraw, apply_interest, transfer

# ---------------------------------------------------------------------------
# 1. Construct some records
# ---------------------------------------------------------------------------

city_branch    = Branch(branch_id="1", reserve="5000000.00")
suburbs_branch = Branch(branch_id="2", reserve="1000000.00")

alice = Account(
    branch=city_branch,
    account_id="10000001",
    balance="1000.00",
    rate="0.0350",      # 3.5 % annual
)

bob = Account(
    branch=suburbs_branch,
    account_id="10000002",
    balance="250.00",
    rate="0.0200",
)

print("=== Initial state ===")
print(repr(alice))
print(repr(bob))

# ---------------------------------------------------------------------------
# 2. Basic operations
# ---------------------------------------------------------------------------

deposit_tx = deposit(alice, "500.00", memo="Initial top-up")
withdraw_tx = withdraw(bob, "75.50", memo="ATM withdrawal")

print("\n=== Transaction with ExternalField (UUID tx_id + memo) ===")
print(repr(deposit_tx))
print(f"tx_id type : {type(deposit_tx.tx_id).__name__}")
print(f"JSON       : {deposit_tx.to_json()}")
restored_tx = type(deposit_tx).from_json(deposit_tx.to_json())
assert restored_tx.tx_id == deposit_tx.tx_id, "tx_id round-trip failed!"
print("tx_id round-trip OK ✓")

print("\n=== After deposit / withdrawal ===")
print(f"Alice balance : {alice.balance}")
print(f"Bob balance   : {bob.balance}")

# ---------------------------------------------------------------------------
# 3. Arithmetic precision — left operand (balance) governs the result
# ---------------------------------------------------------------------------

apply_interest(alice)
apply_interest(bob)

print("\n=== After interest ===")
print(f"Alice balance : {alice.balance}  (rate={alice.rate})")
print(f"Bob balance   : {bob.balance}  (rate={bob.rate})")

# ---------------------------------------------------------------------------
# 4. Transfer between accounts
# ---------------------------------------------------------------------------

transfer(alice, bob, "200.00")

print("\n=== After transfer of 200.00 from Alice to Bob ===")
print(f"Alice balance : {alice.balance}")
print(f"Bob balance   : {bob.balance}")

# ---------------------------------------------------------------------------
# 5. Overflow protection
# ---------------------------------------------------------------------------

print("\n=== Overflow protection ===")
try:
    alice.balance = "99999999999.00"   # exceeds digits=10
except FieldOverflowError as e:
    print(f"Caught: {e}")

print("\n=== signed=False on Branch.reserve ===")
try:
    city_branch.reserve = "-1.00"
except FieldOverflowError as e:
    print(f"Caught: {e}")

# ---------------------------------------------------------------------------
# 6. JSON round-trip
# ---------------------------------------------------------------------------

print("\n=== JSON serialisation ===")
alice_json = alice.to_json()
print(alice_json)

restored = Account.from_json(alice_json)
print(f"Restored balance : {restored.balance}")
print(f"Restored branch  : {restored.branch.branch_id}")
assert alice == restored, "JSON round-trip failed!"
print("Round-trip OK ✓")

# ---------------------------------------------------------------------------
# 7. Fixed-width serialisation (flat-file / mainframe export)
# ---------------------------------------------------------------------------

print("\n=== Fixed-width serialisation ===")
line = alice.to_string()
print(f"Flat line ({len(line)} chars) : {line!r}")

parsed = Account.from_string(line)
print(f"Parsed balance   : {parsed.balance}")
print(f"Parsed branch_id : {parsed.branch.branch_id}")
assert alice == parsed, "Fixed-width round-trip failed!"
print("Round-trip OK ✓")
