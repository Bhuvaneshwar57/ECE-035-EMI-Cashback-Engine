def calculate_refund(purchase_amount, return_fee=0):
    refund_amount = purchase_amount - return_fee
    return refund_amount