"""
Order Validation with Security Checks

Security features:
- MIN/MAX order size (DOS protection)
- Settlement calculation with invariant guarantee
- Price compatibility validation
"""

# Security constants
MIN_ORDER_SIZE_KOPECKS = 100  # 1₽ minimum (DOS protection)
MAX_ORDER_SIZE_KOPECKS = 100_000_000  # 1M₽ maximum (overflow protection)


def validate_order_size(amount_kopecks: int) -> None:
    """
    Validate order size is within safe limits

    DOS Protection: Prevents micro-orders (e.g., 1000 orders at 1 kopeck)
    Overflow Protection: Prevents unreasonably large orders

    Args:
        amount_kopecks: Order amount in kopecks

    Raises:
        ValueError: If amount is below minimum or above maximum

    Examples:
        >>> validate_order_size(100)  # 1₽ - OK
        >>> validate_order_size(50)   # 0.5₽ - raises ValueError
        >>> validate_order_size(100_000_001)  # > 1M₽ - raises ValueError
    """
    if amount_kopecks < MIN_ORDER_SIZE_KOPECKS:
        raise ValueError(
            f"Minimum order: {MIN_ORDER_SIZE_KOPECKS / 100:.2f}₽"
        )

    if amount_kopecks > MAX_ORDER_SIZE_KOPECKS:
        raise ValueError(
            f"Maximum order: {MAX_ORDER_SIZE_KOPECKS / 100:.0f}₽"
        )


def calculate_settlement(amount_kopecks: int, price_bp: int) -> tuple[int, int]:
    """
    Calculate settlement amounts ensuring invariant

    CRITICAL: yes_cost + no_cost MUST equal amount_kopecks (no money created/destroyed)

    Settlement formula:
    - YES pays: floor(amount * price / 10000)
    - NO pays: amount - YES_pays  (ensures sum = amount!)

    Args:
        amount_kopecks: Total amount being matched
        price_bp: YES price in basis points (10000 bp = 100%)

    Returns:
        Tuple of (yes_cost, no_cost) in kopecks

    Examples:
        >>> calculate_settlement(100, 6500)
        (65, 35)  # YES pays 65%, NO pays 35%

        >>> calculate_settlement(100, 3333)
        (33, 67)  # Handles rounding: 33 + 67 = 100 ✓

    Raises:
        ValueError: If settlement doesn't sum to amount (CRITICAL BUG!)
    """
    # Calculate YES cost (floor division for rounding)
    yes_cost = (amount_kopecks * price_bp) // 10000

    # Calculate NO cost (ensures invariant: yes + no = amount)
    no_cost = amount_kopecks - yes_cost

    # CRITICAL: Runtime invariant check (works even with python -O)
    if yes_cost + no_cost != amount_kopecks:
        raise ValueError(
            f"Settlement invariant violated! {yes_cost} + {no_cost} != {amount_kopecks}"
        )

    return yes_cost, no_cost


def is_price_compatible(yes_price_bp: int, no_price_bp: int) -> bool:
    """
    Check if YES and NO prices are compatible for matching

    In a binary prediction market:
    - YES @ P% can only match NO @ (100-P)%
    - Example: YES @ 65% ↔ NO @ 35% ✓ (sum = 100%)
    - Example: YES @ 70% ↔ NO @ 40% ✗ (sum = 110%)

    Args:
        yes_price_bp: YES price in basis points
        no_price_bp: NO price in basis points

    Returns:
        True if prices are compatible (sum = 10000bp), False otherwise

    Examples:
        >>> is_price_compatible(6500, 3500)
        True  # 65% + 35% = 100%

        >>> is_price_compatible(7000, 4000)
        False  # 70% + 40% = 110%
    """
    return yes_price_bp + no_price_bp == 10000
