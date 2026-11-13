
def calculate_bundle_discount(items):
    categories = [item["category"] for item in items]

    discount = 0

    if "TV" in categories and "SOUNDBAR" in categories:
        discount += 2000

    if "PHONE" in categories and "CASE" in categories:
        for item in items:
            if item["category"] == "CASE":
                discount += item["price"] * 0.50

    return discount
