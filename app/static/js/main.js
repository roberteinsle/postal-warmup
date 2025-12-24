// Postal Warmup - Main JavaScript

// Update current time in navbar
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('de-DE', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

// Update time every second
setInterval(updateCurrentTime, 1000);
updateCurrentTime();

// Utility Functions
function formatDateTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDate(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function getStatusBadge(status) {
    const badges = {
        'sent': '<span class="badge bg-success">Gesendet</span>',
        'failed': '<span class="badge bg-danger">Fehlgeschlagen</span>',
        'bounced': '<span class="badge bg-warning text-dark">Zurückgewiesen</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

function getDeliveryBadge(status) {
    const badges = {
        'inbox': '<span class="badge bg-success">Inbox</span>',
        'spam': '<span class="badge bg-danger">Spam</span>',
        'pending': '<span class="badge bg-secondary">Ausstehend</span>',
        'unknown': '<span class="badge bg-warning text-dark">Unbekannt</span>',
        'failed': '<span class="badge bg-danger">Fehlgeschlagen</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

function getContentTypeBadge(type) {
    const badges = {
        'transactional': '<span class="badge bg-info">Transaktional</span>',
        'newsletter': '<span class="badge bg-primary">Newsletter</span>',
        'personal': '<span class="badge bg-success">Persönlich</span>',
        'mixed': '<span class="badge bg-secondary">Gemischt</span>'
    };
    return badges[type] || `<span class="badge bg-secondary">${type}</span>`;
}

// API Request Helper
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showAlert('Fehler: ' + error.message, 'danger');
        throw error;
    }
}

// Show Alert
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Show Loading State
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="text-center"><i class="bi bi-hourglass-split"></i> Lädt...</div>';
    }
}

// Show Error State
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="text-center text-danger"><i class="bi bi-exclamation-triangle"></i> ${message}</div>`;
    }
}
