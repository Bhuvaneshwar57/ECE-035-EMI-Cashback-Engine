
# Decision Log
## ECE-035 – Electronics Retail No-Cost EMI and Cashback Offer Engine

**Team ID:** E005-ECE-035

## Decision 1: Programming Language
- Decision: Python
- Reason: Python supports modular development and CSV processing.
- Status: Implemented

## Decision 2: Data Storage
- Decision: CSV files
- Reason: The project brief provides input data in CSV format.
- Status: Implemented

## Decision 3: Project Structure
- Decision: Separate modules for EMI, cashback, returns and offers.
- Reason: Modular code makes the system easier to understand, test and maintain.
- Status: Verify against implementation

## Decision 4: EMI Eligibility
- Decision: Apply the eligibility threshold defined in the project brief.
- Reason: Purchases below the required minimum should not receive EMI.
- Status: Implemented / Verify

## Decision 5: Cashback Limit
- Decision: Apply the monthly cashback cap for each customer and card.
- Reason: Cashback must not exceed the configured monthly limit.
- Status: Implemented / Verify

## Decision 6: Return Processing
- Decision: Check the return date against the seven-day return window.
- Reason: Cashback reversal must follow the specified business rule.
- Status: Implemented / Verify

## Decision 7: Offer Recommendation
- Decision: Compare the available customer benefits.
- Reason: Recommend the option with the higher benefit.
- Status: Implemented / Verify

## Decision 8: Testing
- Decision: Create separate tests for EMI, cashback, returns and offers.
- Reason: Each important business rule should be checked independently.
- Status: In progress

## Team Notes
- Decisions should reflect the actual implementation.
- Any changes to the original decisions should be recorded here.
