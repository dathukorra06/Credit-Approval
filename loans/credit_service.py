"""
Credit scoring service.
Computes a credit score (0-100) based on historical loan data.
"""
from datetime import date
from loans.models import Loan


def calculate_credit_score(customer) -> int:
    """
    Calculate credit score out of 100 for a customer.

    Components:
      1. Past loans paid on time       (35 pts)
      2. Number of loans taken in past (20 pts)
      3. Loan activity in current year (20 pts)
      4. Loan approved volume          (25 pts)
      5. Override: if current debt > approved limit → score = 0
    """
    all_loans = Loan.objects.filter(customer=customer)

    # Rule 5: if total current debt > approved limit, score = 0
    active_loans = [l for l in all_loans if l.is_active]
    current_debt_sum = sum(l.loan_amount for l in active_loans)
    if current_debt_sum > customer.approved_limit:
        return 0

    total_loans = all_loans.count()
    if total_loans == 0:
        # No history → moderate score
        return 50

    # --- Component 1: Past loans paid on time (35 pts) ---
    total_emis = sum(l.tenure for l in all_loans)
    total_on_time = sum(l.emis_paid_on_time for l in all_loans)
    on_time_ratio = total_on_time / total_emis if total_emis > 0 else 0
    score_on_time = on_time_ratio * 35

    # --- Component 2: Number of loans taken (20 pts) ---
    # Penalise excessive loans (>10 is risky)
    if total_loans <= 2:
        score_num_loans = 20
    elif total_loans <= 5:
        score_num_loans = 16
    elif total_loans <= 10:
        score_num_loans = 10
    else:
        score_num_loans = 5

    # --- Component 3: Loan activity in current year (20 pts) ---
    current_year = date.today().year
    loans_this_year = all_loans.filter(start_date__year=current_year).count()
    if loans_this_year == 0:
        score_activity = 20
    elif loans_this_year <= 2:
        score_activity = 15
    elif loans_this_year <= 4:
        score_activity = 8
    else:
        score_activity = 3

    # --- Component 4: Loan approved volume (25 pts) ---
    total_volume = sum(l.loan_amount for l in all_loans)
    volume_ratio = min(total_volume / customer.approved_limit, 1.0) if customer.approved_limit > 0 else 1.0
    # Lower volume relative to limit is better
    score_volume = (1 - volume_ratio) * 25

    credit_score = int(score_on_time + score_num_loans + score_activity + score_volume)
    return min(100, max(0, credit_score))


def get_loan_eligibility(customer, loan_amount: float, interest_rate: float, tenure: int) -> dict:
    """
    Given a customer and requested loan parameters, return eligibility result.

    Returns:
        {
            'approved': bool,
            'corrected_interest_rate': float,
            'monthly_installment': float,
            'credit_score': int,
        }
    """
    credit_score = calculate_credit_score(customer)

    # Check if sum of current EMIs > 50% of monthly salary
    active_loans = [l for l in Loan.objects.filter(customer=customer) if l.is_active]
    current_emis = sum(l.monthly_repayment for l in active_loans)
    if current_emis > 0.5 * customer.monthly_salary:
        monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
        return {
            'approved': False,
            'corrected_interest_rate': interest_rate,
            'monthly_installment': monthly_installment,
            'credit_score': credit_score,
            'rejection_reason': 'Current EMIs exceed 50% of monthly salary',
        }

    # Determine minimum required rate based on credit score
    approved = False
    corrected_rate = interest_rate

    if credit_score > 50:
        approved = True
        corrected_rate = interest_rate

    elif 30 < credit_score <= 50:
        if interest_rate > 12:
            approved = True
            corrected_rate = interest_rate
        else:
            approved = True
            corrected_rate = 12.0  # correct to minimum slab rate

    elif 10 < credit_score <= 30:
        if interest_rate > 16:
            approved = True
            corrected_rate = interest_rate
        else:
            approved = True
            corrected_rate = 16.0  # correct to minimum slab rate

    else:  # credit_score <= 10
        approved = False
        corrected_rate = interest_rate

    monthly_installment = calculate_monthly_installment(loan_amount, corrected_rate, tenure)

    result = {
        'approved': approved,
        'corrected_interest_rate': corrected_rate,
        'monthly_installment': monthly_installment,
        'credit_score': credit_score,
    }

    if not approved:
        result['rejection_reason'] = 'Credit score too low'

    return result


def calculate_monthly_installment(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Calculate EMI using compound interest formula (reducing balance / standard EMI).

    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where r = monthly interest rate = annual_rate / 12 / 100
          n = tenure in months
    """
    if annual_rate == 0:
        return round(principal / tenure_months, 2)

    monthly_rate = annual_rate / 12 / 100
    n = tenure_months
    emi = principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)
    return round(emi, 2)
