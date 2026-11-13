import csv
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from datetime import date


# -------------------- Money and CSV helpers --------------------

def money(value):
    """Convert a value to money with two decimal places."""
    return Decimal(str(value)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def read_csv(filename):
    with open(filename, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(filename, headers, rows):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def format_money(value):
    return f"{money(value):.2f}"


# -------------------- Load input data --------------------

bills = {row["bill_id"]: row for row in read_csv("bills.csv")}

items = {}
for row in read_csv("bill_items.csv"):
    items.setdefault(row["bill_id"], []).append(row)

returns = {row["return_id"]: row for row in read_csv("returns.csv")}

config = {}
cards = {}


# -------------------- Store processing results --------------------

summary_rows = []
schedule_rows = []
return_rows = []

# Total cashback granted and reversed for each month/customer/card.
cashback_granted = {}
cashback_reversed = {}

# Information required when a return command is processed.
bill_results = {}

report_month = None


# -------------------- Process commands in file order --------------------

with open("commands.txt", "r", encoding="utf-8-sig") as command_file:
    for line in command_file:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split("|")
        command = parts[0].strip()

        # Load offer configuration.
        if command == "LOAD_CONFIG":
            for row in read_csv(parts[1].strip()):
                config[row["parameter"]] = row["value"]

        # Load card eligibility details.
        elif command == "LOAD_CARDS":
            for row in read_csv(parts[1].strip()):
                cards[row["issuer_code"]] = row

        # -------------------- Process a bill --------------------
        elif command == "BILL":
            bill_id = parts[1].strip()
            bill = bills[bill_id]
            bill_items = items.get(bill_id, [])

            customer = bill["customer_id"]
            issuer = bill["card_issuer"]
            bill_date = bill["bill_date"]
            month = bill_date[:7]
            card = cards[issuer]

            gross = sum(
                (money(item["price"]) for item in bill_items),
                Decimal("0.00")
            )

            # Calculate bundle discounts before EMI/cashback.
            categories = [item["category"] for item in bill_items]
            bundle_discount = Decimal("0.00")

            if "TV" in categories and "SOUNDBAR" in categories:
                bundle_discount += money(
                    config["BUNDLE_TV_SOUNDBAR_OFF"]
                )

            if "PHONE" in categories and "CASE" in categories:
                case_percentage = Decimal(
                    config["BUNDLE_PHONE_CASE_PCT_OFF_CASE"]
                )
                for item in bill_items:
                    if item["category"] == "CASE":
                        bundle_discount += money(
                            money(item["price"]) * case_percentage
                            / Decimal("100")
                        )

            bill_amount = max(
                Decimal("0.00"), gross - bundle_discount
            )

            # -------------------- Check EMI eligibility --------------------
            tenure_text = bill["tenure_months"].strip()
            tenure = int(tenure_text) if tenure_text else 0

            allowed_tenures = [
                int(value)
                for value in config["EMI_TENURES"].split(";")
            ]

            emi_available = (
                card["emi_eligible"].strip().lower() == "true"
                and bill_amount >= money(config["EMI_MIN_BILL"])
                and tenure in allowed_tenures
            )

            interest_saved = Decimal("0.00")
            instalment = Decimal("0.00")
            last_instalment = Decimal("0.00")
            processing_fee = Decimal("0.00")
            emi_parts = []

            if emi_available:
                # This is the processing fee applicable to the EMI option.
                # It is charged in the schedule only if EMI is recommended.
                if bill_amount < money(
                    config["PROCESSING_FEE_WAIVED_FROM"]
                ):
                    processing_fee = money(config["PROCESSING_FEE"])

                annual_rate = Decimal(config["EMI_INTEREST_PA_PCT"])
                interest_saved = money(
                    bill_amount * annual_rate * tenure
                    / Decimal("1200")
                )

                # Round each regular instalment up to the next rupee.
                instalment = (bill_amount / tenure).quantize(
                    Decimal("1"), rounding=ROUND_CEILING
                )

                for _ in range(tenure - 1):
                    emi_parts.append(instalment)

                # Adjust the final instalment so the base total is exact.
                last_instalment = bill_amount - sum(
                    emi_parts, Decimal("0.00")
                )
                emi_parts.append(last_instalment)

            # -------------------- Check cashback eligibility --------------------
            cashback_eligible = (
                card["cashback_eligible"].strip().lower() == "true"
            )

            cap_key = (month, customer, issuer)
            already_granted = cashback_granted.get(
                cap_key, Decimal("0.00")
            )
            already_reversed = cashback_reversed.get(
                cap_key, Decimal("0.00")
            )

            # A qualifying return restores the used monthly cap.
            cashback_used = max(
                Decimal("0.00"), already_granted - already_reversed
            )

            possible_cashback = Decimal("0.00")
            if cashback_eligible:
                cashback_percentage = Decimal(config["CASHBACK_PCT"])
                cashback_cap = money(
                    config["CASHBACK_CAP_PER_CARD_CUSTOMER_MONTH"]
                )
                possible_cashback = money(
                    bill_amount * cashback_percentage / Decimal("100")
                )
                remaining_cap = max(
                    Decimal("0.00"), cashback_cap - cashback_used
                )
                possible_cashback = min(
                    possible_cashback, remaining_cap
                )

            # -------------------- Recommend one offer --------------------
            if emi_available and cashback_eligible:
                if interest_saved > possible_cashback:
                    recommendation = "EMI"
                else:
                    # Cashback wins ties.
                    recommendation = "CASHBACK"
            elif emi_available:
                recommendation = "EMI"
            elif cashback_eligible:
                recommendation = "CASHBACK"
            else:
                recommendation = "NONE"

            benefit = Decimal("0.00")
            cashback_amount = Decimal("0.00")

            
            if recommendation == "EMI":
                benefit = interest_saved

                # Rebuild all instalments
                emi_parts = [instalment] * (tenure - 1)
                emi_parts.append(last_instalment)

                # Add processing fee to first instalment
                emi_parts[0] += processing_fee

                for number, amount in enumerate(emi_parts, start=1):
                    schedule_rows.append({
                        "bill_id": bill_id,
                        "instalment_no": number,
                        "amount": format_money(amount)
                    })

            elif recommendation == "CASHBACK":
                cashback_amount = possible_cashback
                benefit = cashback_amount
                cashback_granted[cap_key] = (
                    already_granted + cashback_amount
                )
                cashback_reversed.setdefault(
                    cap_key, Decimal("0.00")
                )

            # Store bill details for a possible return command.
            bill_results[bill_id] = {
                "customer": customer,
                "issuer": issuer,
                "month": month,
                "date": bill_date,
                "recommendation": recommendation,
                "cashback": cashback_amount,
                "reversed": Decimal("0.00"),
                "bill_amount": bill_amount,
                "return_reversed": False
            }

            summary_rows.append({
                "bill_id": bill_id,
                "customer_id": customer,
                "bill_date": bill_date,
                "card_issuer": issuer,
                "gross_amount": format_money(gross),
                "bundle_discount": format_money(bundle_discount),
                "bill_amount": format_money(bill_amount),
                "emi_available": str(emi_available).lower(),
                "tenure_months": tenure_text,
                "instalment": (
                    format_money(instalment)
                    if emi_available else ""
                ),
                "last_instalment": (
                    format_money(last_instalment)
                    if emi_available else ""
                ),
                "processing_fee": format_money(processing_fee),
                "interest_saved": format_money(interest_saved),
                "cashback_eligible": str(cashback_eligible).lower(),
                "cashback_amount": format_money(cashback_amount),
                "recommended_option": recommendation,
                "benefit_amount": format_money(benefit)
            })

        # -------------------- Process a return --------------------
        elif command == "RETURN":
            return_id = parts[1].strip()
            ret = returns[return_id]

            bill_id = ret["bill_id"]
            line_no = int(ret["line_no"])
            return_date = ret["return_date"]

            original_bill = bills[bill_id]
            bill_date_value = date.fromisoformat(
                original_bill["bill_date"]
            )
            returned_on = date.fromisoformat(return_date)
            days_after_bill = (returned_on - bill_date_value).days

            within_window = (
                0 <= days_after_bill
                <= int(config["RETURN_WINDOW_DAYS"])
            )

            reversed_amount = Decimal("0.00")
            result = bill_results.get(bill_id)

            # The brief says the full cashback from that bill is reversed
            # when an item is returned within the return window.
            # Multiple returns for the same bill must not reverse it twice.
            if (
                within_window
                and result is not None
                and result["recommendation"] == "CASHBACK"
                and not result["return_reversed"]
            ):
                reversed_amount = result["cashback"]
                result["reversed"] = reversed_amount
                result["return_reversed"] = True

                cap_key = (
                    result["month"],
                    result["customer"],
                    result["issuer"]
                )
                cashback_reversed[cap_key] = (
                    cashback_reversed.get(
                        cap_key, Decimal("0.00")
                    ) + reversed_amount
                )

            return_rows.append({
                "return_id": return_id,
                "bill_id": bill_id,
                "line_no": line_no,
                "return_date": return_date,
                "days_after_bill": days_after_bill,
                "within_window": str(within_window).lower(),
                "cashback_reversed": format_money(reversed_amount)
            })

        # Remember which month to include in the cashback report.
        elif command == "PRINT_CASHBACK_REPORT":
            report_month = parts[1].strip()


# -------------------- Write required output files --------------------

write_csv(
    "offer_summary.csv",
    [
        "bill_id", "customer_id", "bill_date", "card_issuer",
        "gross_amount", "bundle_discount", "bill_amount",
        "emi_available", "tenure_months", "instalment",
        "last_instalment", "processing_fee", "interest_saved",
        "cashback_eligible", "cashback_amount",
        "recommended_option", "benefit_amount"
    ],
    summary_rows
)

write_csv(
    "emi_schedule.csv",
    ["bill_id", "instalment_no", "amount"],
    schedule_rows
)

write_csv(
    "returns_log.csv",
    [
        "return_id", "bill_id", "line_no", "return_date",
        "days_after_bill", "within_window", "cashback_reversed"
    ],
    return_rows
)

# -------------------- Create monthly cashback report --------------------

report_rows = []

if report_month:
    all_keys = set(cashback_granted) | set(cashback_reversed)
    cap = money(config["CASHBACK_CAP_PER_CARD_CUSTOMER_MONTH"])

    for key in sorted(all_keys):
        month, customer, issuer = key
        if month != report_month:
            continue

        granted = cashback_granted.get(key, Decimal("0.00"))
        reversed_value = cashback_reversed.get(key, Decimal("0.00"))
        net_liability = max(
            Decimal("0.00"), granted - reversed_value
        )

        report_rows.append({
            "month": month,
            "customer_id": customer,
            "card_issuer": issuer,
            "cashback_granted": format_money(granted),
            "cashback_reversed": format_money(reversed_value),
            "net_liability": format_money(net_liability),
            "cap_remaining": format_money(
                max(Decimal("0.00"), cap - net_liability)
            )
        })

write_csv(
    "cashback_report.csv",
    [
        "month", "customer_id", "card_issuer",
        "cashback_granted", "cashback_reversed",
        "net_liability", "cap_remaining"
    ],
    report_rows
)

print("ECE-035 Offer Engine completed successfully!")
print("Bills processed:", len(summary_rows))
print("EMI instalments generated:", len(schedule_rows))
print("Returns processed:", len(return_rows))
print("Output CSV files created successfully.")
