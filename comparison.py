def compare_offers(offers):
    best_offer = max(offers, key=lambda x: x["discount"])

    return best_offer