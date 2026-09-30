// DOM Elements for SPA Navigation
const layerAuth = document.getElementById('layer-auth');
const layerPaywall = document.getElementById('layer-paywall');
const layerApp = document.getElementById('layer-app');

// Auth DOM Elements
const authForm = document.getElementById('auth-form');
const tabSignin = document.getElementById('tab-signin');
const tabSignup = document.getElementById('tab-signup');
const authSubmitBtn = document.getElementById('auth-submit-btn');

// Paywall DOM Elements
const btnFreeUse = document.getElementById('btn-free-use');
const btnPay = document.getElementById('btn-pay'); // May be null if replaced with a link

// App DOM Elements
const btnLogout = document.getElementById('btn-logout');
const decideForm = document.getElementById('decide-form');

// --- Navigation Logic ---
function showLayer(layerElement) {
    // Hide all layers
    layerAuth.classList.remove('active');
    layerPaywall.classList.remove('active');
    layerApp.classList.remove('active');
    
    // Show the requested layer after a tiny delay for CSS transition
    setTimeout(() => {
        layerElement.classList.add('active');
    }, 50);
}

// --- Auth Logic ---
tabSignin.addEventListener('click', () => {
    tabSignin.classList.add('active');
    tabSignup.classList.remove('active');
    authSubmitBtn.textContent = 'Continue to Platform';
});

tabSignup.addEventListener('click', () => {
    tabSignup.classList.add('active');
    tabSignin.classList.remove('active');
    authSubmitBtn.textContent = 'Create Account';
});

authForm.addEventListener('submit', (e) => {
    e.preventDefault();
    // Simulate auth success and go to paywall
    showLayer(layerPaywall);
});

// --- Paywall Logic ---
btnFreeUse.addEventListener('click', () => {
    showLayer(layerApp);
});

if (btnPay) {
    btnPay.addEventListener('click', () => {
        // Simulate successful Stripe payment
        const originalText = btnPay.textContent;
        btnPay.textContent = 'Processing...';
        btnPay.disabled = true;
        
        setTimeout(() => {
            btnPay.textContent = 'Success!';
            btnPay.style.background = '#10b981'; // Green
            
            setTimeout(() => {
                showLayer(layerApp);
                // Reset button
                btnPay.textContent = originalText;
                btnPay.style.background = '';
                btnPay.disabled = false;
            }, 1000);
        }, 1500);
    });
}

// --- App Navigation Logic ---
btnLogout.addEventListener('click', () => {
    // Clear forms and reset
    authForm.reset();
    decideForm.reset();
    document.getElementById('results').innerHTML = '<p>Submit the configuration to see sizing and alignment details.</p>';
    document.getElementById('results').className = 'results-empty';
    
    showLayer(layerAuth);
});

// --- Trade Configuration Logic (Original) ---
decideForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const payload = {
        equity: parseFloat(document.getElementById('equity').value),
        entry: parseFloat(document.getElementById('entry').value),
        invalidation: parseFloat(document.getElementById('invalidation').value),
        adv: parseFloat(document.getElementById('adv').value),
        spread: parseFloat(document.getElementById('spread').value),
        stock_rs: parseFloat(document.getElementById('stock_rs').value),
        group_rs: parseFloat(document.getElementById('group_rs').value),
        regime: document.getElementById('regime').value
    };
    
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="results-empty" style="padding: 20px 0;">Analyzing risk parameters...</div>';
    
    try {
        const response = await fetch('/api/decide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        let html = `<div class="result-card">`;
        
        if (data.accepted) {
            html += `<div class="status-badge status-accept">TRADE ACCEPTED</div>`;
        } else {
            html += `<div class="status-badge status-reject">STAND ASIDE</div>`;
        }
        
        html += `
            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">Approved Shares</div>
                    <div class="metric-value">${data.shares}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Planned Loss</div>
                    <div class="metric-value">$${data.planned_loss.toFixed(2)}</div>
                </div>
                <div class="metric" style="grid-column: span 2">
                    <div class="metric-label">Market Alignment</div>
                    <div class="metric-value" style="text-transform: capitalize; font-size: 1.2rem;">${data.alignment.replace('_', ' ')}</div>
                </div>
            </div>
        `;
        
        if (data.reasons && data.reasons.length > 0) {
            html += `<div class="alerts">`;
            data.reasons.forEach(r => {
                html += `<div class="alert-item">${r}</div>`;
            });
            html += `</div>`;
        }
        
        if (data.warnings && data.warnings.length > 0) {
            html += `<div class="alerts" style="margin-top: 12px;">`;
            data.warnings.forEach(w => {
                html += `<div class="warning-item">${w}</div>`;
            });
            html += `</div>`;
        }
        
        html += `</div>`;
        resultsDiv.innerHTML = html;
        resultsDiv.className = ''; // Remove empty class
        
    } catch (err) {
        resultsDiv.innerHTML = `<div class="alert-item">Error connecting to server. Is it running?</div>`;
    }
});
