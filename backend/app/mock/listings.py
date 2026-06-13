"""Pre-prepared listing data for FB Marketplace (always mock) and Vinted fallback."""

FACEBOOK_LISTINGS = [
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Space Grey — top condition",
        "price_text": "€185",
        "location": "Schwabing, München",
        "url": "https://www.facebook.com/marketplace/item/mock-001",
        "seller_rating": 4.7,
        "seller_reviews": 18,
        "raw_description": "iPhone 14 128GB Space Grey. Sehr guter Zustand, keine Kratzer. Original-Verpackung vorhanden. Akku 94%.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 Pro 256GB Deep Purple",
        "price_text": "€350",
        "location": "Maxvorstadt, München",
        "url": "https://www.facebook.com/marketplace/item/mock-002",
        "seller_rating": 4.2,
        "seller_reviews": 5,
        "raw_description": "iPhone 14 Pro 256GB Deep Purple. Gut erhalten. Kleiner Kratzer auf der Rückseite.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Starlight",
        "price_text": "€170",
        "location": "Pasing, München",
        "url": "https://www.facebook.com/marketplace/item/mock-003",
        "seller_rating": 3.8,
        "seller_reviews": 3,
        "raw_description": "iPhone 14 128GB Starlight. Gebraucht, aber funktioniert einwandfrei. Ein paar kleine Gebrauchsspuren.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Midnight — wie neu",
        "price_text": "€195",
        "location": "Bogenhausen, München",
        "url": "https://www.facebook.com/marketplace/item/mock-004",
        "seller_rating": 4.9,
        "seller_reviews": 42,
        "raw_description": "iPhone 14 128GB Midnight. Wie neu, 2 Monate alt. Mit Hülle und Original-Kabel.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 256GB Blue — guter Zustand",
        "price_text": "€210",
        "location": "Sendling, München",
        "url": "https://www.facebook.com/marketplace/item/mock-005",
        "seller_rating": 4.5,
        "seller_reviews": 11,
        "raw_description": "iPhone 14 256GB Blue. Guter Zustand. Displayschutz drauf seit Tag 1.",
    },
]

# The seller's real item, presented as a Kleinanzeigen listing. Image search matches this.
SEEDED_DEMO_LISTING = {
    "platform": "kleinanzeigen",
    "listing_id": "demo-seed-001",
    "title": "iPhone 14 128GB Midnight — wie neu",
    "price_text": "€185",
    "location": "Schwabing, München",
    "url": "https://www.kleinanzeigen.de/s-anzeige/demo-seed-001",
    "image_url": "https://example.com/REPLACE_WITH_REAL_PHOTO.jpg",
    "seller_rating": 4.9,
    "seller_reviews": 24,
    "raw_description": "iPhone 14 128GB Midnight. Wie neu, kaum benutzt. Mit Originalverpackung.",
    "match_keywords": ["iphone", "14", "128", "midnight"],
}

VINTED_FALLBACK_LISTINGS = [
    {
        "platform": "vinted",
        "title": "iPhone 14 128GB – sehr gut",
        "price_text": "€180",
        "location": "München",
        "url": "https://www.vinted.de/items/mock-v001",
        "seller_rating": 5.0,
        "seller_reviews": 67,
        "raw_description": "iPhone 14 128GB sehr guter Zustand. Akku 91%. Mit Originalzubehör.",
    },
    {
        "platform": "vinted",
        "title": "iPhone 14 Pro 128GB",
        "price_text": "€320",
        "location": "München Ost",
        "url": "https://www.vinted.de/items/mock-v002",
        "seller_rating": 4.6,
        "seller_reviews": 23,
        "raw_description": "iPhone 14 Pro 128GB Space Black. Normale Gebrauchsspuren.",
    },
]
