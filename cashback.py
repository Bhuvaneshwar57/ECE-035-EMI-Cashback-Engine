
def calculate_cashback(bill_amount, previous_cashback):
    cashback = bill_amount * 0.10

    remaining_limit = 1500 - previous_cashback

    if cashback > remaining_limit:
        cashback = remaining_limit

    if cashback < 0:
        cashback = 0

    return cashback
