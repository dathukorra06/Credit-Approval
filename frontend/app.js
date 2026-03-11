const API_BASE = 'http://localhost:8000';

// Tab Switching Logic
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
        // Update active tab styling
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');

        // Update view
        const targetId = e.target.getAttribute('data-target');
        document.querySelectorAll('.card').forEach(c => c.classList.remove('active-section'));
        document.getElementById(targetId).classList.add('active-section');
    });
});

// Utility for formatting currency
const formatMoney = (amount) => {
    return new Intl.NumberFormat('en-IN').format(amount);
};

// Form 1: Register Customer
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const btn = e.target.querySelector('button');
    const textSpan = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');

    // UI Loading state
    textSpan.classList.add('hidden');
    loader.classList.remove('hidden');
    btn.disabled = true;

    const payload = {
        first_name: document.getElementById('reg-first-name').value,
        last_name: document.getElementById('reg-last-name').value,
        age: parseInt(document.getElementById('reg-age').value),
        monthly_income: parseInt(document.getElementById('reg-income').value),
        phone_number: parseInt(document.getElementById('reg-phone').value)
    };

    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('res-cust-id').innerText = data.customer_id;
            document.getElementById('res-limit').innerText = formatMoney(data.approved_limit);
            document.getElementById('res-income').innerText = formatMoney(data.monthly_income);
            document.getElementById('register-result').classList.remove('hidden');
        } else {
            alert(data.error || 'Failed to register customer. Note: Check if phone number is unique.');
        }

    } catch (error) {
        alert('Network Error! Make sure Backend server is running on localhost:8000');
    } finally {
        textSpan.classList.remove('hidden');
        loader.classList.add('hidden');
        btn.disabled = false;
    }
});


// Form 2: Check Eligibility
document.getElementById('eligibility-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const btn = e.target.querySelector('button');
    const textSpan = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');

    // UI Loading state
    textSpan.classList.add('hidden');
    loader.classList.remove('hidden');
    btn.disabled = true;

    const payload = {
        customer_id: parseInt(document.getElementById('el-customer-id').value),
        loan_amount: parseFloat(document.getElementById('el-amount').value),
        interest_rate: parseFloat(document.getElementById('el-rate').value),
        tenure: parseInt(document.getElementById('el-tenure').value)
    };

    try {
        const response = await fetch(`${API_BASE}/check-eligibility`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            // Update decision banner visual logic
            const banner = document.getElementById('el-decision-banner');
            const iconApp = document.getElementById('el-icon-approved');
            const iconRej = document.getElementById('el-icon-rejected');
            const headerText = document.getElementById('el-approval-text');
            const subText = document.getElementById('el-subtext');

            banner.className = 'status-banner'; // reset classes
            iconApp.classList.add('hidden');
            iconRej.classList.add('hidden');

            if (data.approval) {
                banner.classList.add('approved');
                iconApp.classList.remove('hidden');
                headerText.innerText = "Loan Approved";
                subText.innerText = "Based on credit score calculations, you meet the criteria.";
            } else {
                banner.classList.add('rejected');
                iconRej.classList.remove('hidden');
                headerText.innerText = "Loan Rejected";
                subText.innerText = data.rejection_reason || "Credit score is too low or active debt is too high.";
            }

            // Update stats
            document.getElementById('el-res-emi').innerText = formatMoney(data.monthly_installment);
            document.getElementById('el-res-req-rate').innerText = data.interest_rate;
            document.getElementById('el-res-cor-rate').innerText = data.corrected_interest_rate;

            // Show result area
            document.getElementById('eligibility-result').classList.remove('hidden');

        } else {
            alert(data.error || 'Failed to check eligibility.');
        }

    } catch (error) {
        alert('Network Error! Make sure Backend server is running on localhost:8000');
    } finally {
        textSpan.classList.remove('hidden');
        loader.classList.add('hidden');
        btn.disabled = false;
    }
});
