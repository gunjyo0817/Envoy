"""Deterministic mock seller that simulates counter-offer / accept / reject."""
import datetime

def mock_seller_response(listing_price: float, buyer_offer: float) -> dict:
    """
    Returns a NegotiationMessage dict simulating a seller reply.
    - offer >= 95% of listing_price  → accept
    - offer >= 82% of listing_price  → counter at listing_price * 0.92
    - offer <  82% of listing_price  → reject
    """
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if buyer_offer >= listing_price * 0.95:
        return {
            "role": "seller",
            "text": f"OK, einverstanden. €{buyer_offer:.0f} ist gut für mich.",
            "act": "accept",
            "price": buyer_offer,
            "ts": ts,
        }
    elif buyer_offer >= listing_price * 0.82:
        counter = round(listing_price * 0.92)
        return {
            "role": "seller",
            "text": f"Hmm, €{buyer_offer:.0f} ist etwas wenig. Ich mache es für €{counter}.",
            "act": "counter_offer",
            "price": float(counter),
            "ts": ts,
        }
    else:
        return {
            "role": "seller",
            "text": f"Tut mir leid, €{buyer_offer:.0f} ist zu wenig. Preis ist fest.",
            "act": "reject",
            "price": None,
            "ts": ts,
        }
