"""Round displayed cost lines and reconcile them with the displayed total."""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import TypedDict

CURRENCY_QUANTUM = Decimal("0.01")


class CostDisplay(TypedDict):
    """Two-decimal amounts for a dashboard cost breakdown."""

    total: str
    lines: dict[str, str]


def cost_display(total: Decimal, amounts: dict[str, Decimal]) -> CostDisplay:
    """Format the total and lines, including any signed rounding difference."""
    with localcontext() as context:
        # Leave room for cents and a carry when adding rounded amounts.
        context.prec = max(
            context.prec,
            max(amount.adjusted() for amount in (total, *amounts.values())) + 4,
        )
        rounded_total = total.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_EVEN)
        rounded = {
            key: amount.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_EVEN)
            for key, amount in amounts.items()
        }
        difference = rounded_total - sum(rounded.values(), Decimal(0))

    lines = {key: str(amount) if amount else "0.00" for key, amount in rounded.items()}
    if difference:
        lines["rounding_adjustment"] = f"{difference:+.2f}"
    return {"total": str(rounded_total) if rounded_total else "0.00", "lines": lines}
