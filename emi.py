
def calculate_emi(bill_amount, tenure):
    monthly_emi = (bill_amount + tenure - 1) // tenure

    installments = []

    for i in range(tenure):
        installments.append(monthly_emi)

    installments[-1] = bill_amount - sum(installments[:-1])

    return installments


def calculate_processing_fee(bill_amount):
    if bill_amount < 25000:
        return 199
    else:
        return 0

