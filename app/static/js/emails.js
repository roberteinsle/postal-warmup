// Emails Page JavaScript

let currentPage = 1;
let currentFilters = {};

// Load emails with pagination and filters
async function loadEmails(page = 1) {
    try {
        currentPage = page;

        const params = new URLSearchParams({
            page: page,
            per_page: 25,
            ...currentFilters
        });

        const data = await apiRequest(`/emails/api/list?${params}`);

        // Update table
        const tbody = document.getElementById('emails-table-body');
        if (data.emails.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">Keine Emails gefunden</td></tr>';
        } else {
            tbody.innerHTML = data.emails.map(email => `
                <tr onclick="showEmailDetails(${email.id})">
                    <td>${email.id}</td>
                    <td>${formatDateTime(email.sent_at)}</td>
                    <td>${email.sender}</td>
                    <td>${email.recipient}</td>
                    <td>${email.subject.substring(0, 50)}...</td>
                    <td>${getContentTypeBadge(email.content_type)}</td>
                    <td>${getStatusBadge(email.status)}</td>
                    <td>${getDeliveryBadge(email.delivery_status)}</td>
                    <td>${email.is_read ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-circle text-muted"></i>'}</td>
                </tr>
            `).join('');
        }

        // Update pagination
        renderPagination(data.pagination);

    } catch (error) {
        console.error('Failed to load emails:', error);
        showError('emails-table-body', 'Fehler beim Laden der Emails');
    }
}

// Render pagination
function renderPagination(pagination) {
    const paginationEl = document.getElementById('pagination');
    if (!pagination || pagination.pages <= 1) {
        paginationEl.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    html += `
        <li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadEmails(${pagination.page - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
    `;

    // Page numbers
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<li class="page-item active"><a class="page-link" href="#">${i}</a></li>`;
        } else if (i === 1 || i === pagination.pages || Math.abs(i - pagination.page) <= 2) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadEmails(${i}); return false;">${i}</a></li>`;
        } else if (Math.abs(i - pagination.page) === 3) {
            html += `<li class="page-item disabled"><a class="page-link" href="#">...</a></li>`;
        }
    }

    // Next button
    html += `
        <li class="page-item ${!pagination.has_next ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadEmails(${pagination.page + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;

    paginationEl.innerHTML = html;
}

// Apply filters
function applyFilters() {
    const search = document.getElementById('search-input').value;
    const status = document.getElementById('status-filter').value;
    const delivery = document.getElementById('delivery-filter').value;

    currentFilters = {};
    if (search) currentFilters.search = search;
    if (status) currentFilters.status = status;
    if (delivery) currentFilters.delivery_status = delivery;

    loadEmails(1);
}

// Clear filters
function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('status-filter').value = '';
    document.getElementById('delivery-filter').value = '';

    currentFilters = {};
    loadEmails(1);
}

// Show email details
async function showEmailDetails(emailId) {
    try {
        const email = await apiRequest(`/emails/api/${emailId}`);

        alert(`Email Details:\n\n` +
              `Von: ${email.sender}\n` +
              `An: ${email.recipient}\n` +
              `Betreff: ${email.subject}\n` +
              `Status: ${email.status}\n` +
              `Zustellung: ${email.delivery_status}\n` +
              `Gesendet: ${formatDateTime(email.sent_at)}\n\n` +
              `Inhalt:\n${email.body}`);

    } catch (error) {
        showAlert('Fehler beim Laden der Email-Details', 'danger');
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadEmails(1);

    // Enter key on search
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') applyFilters();
    });
});
