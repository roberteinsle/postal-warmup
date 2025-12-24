// Dashboard JavaScript

let volumeChart, successChart;

// Load dashboard data
async function loadDashboard() {
    await Promise.all([
        loadOverviewStats(),
        loadChartData(),
        loadRecentEmails(),
        loadSchedulerStatus()
    ]);
}

// Load overview statistics
async function loadOverviewStats() {
    try {
        const data = await apiRequest('/api/stats/overview');

        // Warmup progress
        document.getElementById('warmup-current-day').textContent = data.warmup.current_day;
        document.getElementById('warmup-total-days').textContent = data.warmup.total_days;

        const progressBar = document.getElementById('warmup-progress-bar');
        progressBar.style.width = data.warmup.progress_percent + '%';
        progressBar.textContent = data.warmup.progress_percent + '%';

        document.getElementById('today-sent').textContent = data.warmup.today_sent;
        document.getElementById('today-target').textContent = data.warmup.today_target;

        const statusBadge = document.getElementById('today-status-badge');
        if (data.warmup.today_completed) {
            statusBadge.className = 'badge bg-success ms-2';
            statusBadge.textContent = 'Abgeschlossen';
        } else if (data.warmup.today_sent > 0) {
            statusBadge.className = 'badge bg-warning ms-2';
            statusBadge.textContent = 'Läuft...';
        } else {
            statusBadge.className = 'badge bg-secondary ms-2';
            statusBadge.textContent = 'Ausstehend';
        }

        // Overall stats
        document.getElementById('stat-total-sent').textContent = data.overall.total_sent;
        document.getElementById('stat-inbox-rate').textContent = data.overall.success_rate + '%';
        document.getElementById('stat-total-inbox').textContent = data.overall.total_inbox;
        document.getElementById('stat-spam-rate').textContent = data.overall.spam_rate + '%';
        document.getElementById('stat-total-spam').textContent = data.overall.total_spam;
        document.getElementById('stat-pending').textContent = data.overall.total_pending;

    } catch (error) {
        console.error('Failed to load overview stats:', error);
    }
}

// Load chart data
async function loadChartData() {
    try {
        const data = await apiRequest('/api/stats/chart');

        const labels = data.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
        });

        // Volume Chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        if (volumeChart) volumeChart.destroy();

        volumeChart = new Chart(volumeCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Gesendet',
                        data: data.map(d => d.sent),
                        backgroundColor: 'rgba(13, 110, 253, 0.7)',
                        borderColor: 'rgba(13, 110, 253, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Inbox',
                        data: data.map(d => d.inbox),
                        backgroundColor: 'rgba(25, 135, 84, 0.7)',
                        borderColor: 'rgba(25, 135, 84, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Spam',
                        data: data.map(d => d.spam),
                        backgroundColor: 'rgba(255, 193, 7, 0.7)',
                        borderColor: 'rgba(255, 193, 7, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Success Rate Chart
        const successCtx = document.getElementById('successChart').getContext('2d');
        if (successChart) successChart.destroy();

        successChart = new Chart(successCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Erfolgsrate %',
                        data: data.map(d => d.success_rate),
                        borderColor: 'rgba(25, 135, 84, 1)',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Spam-Rate %',
                        data: data.map(d => d.spam_rate),
                        borderColor: 'rgba(220, 53, 69, 1)',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

    } catch (error) {
        console.error('Failed to load chart data:', error);
    }
}

// Load recent emails
async function loadRecentEmails() {
    try {
        const emails = await apiRequest('/api/stats/recent-emails');

        const tbody = document.getElementById('recent-emails-body');
        if (emails.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Keine Emails vorhanden</td></tr>';
            return;
        }

        tbody.innerHTML = emails.map(email => `
            <tr>
                <td>${formatDateTime(email.sent_at)}</td>
                <td>${email.sender}</td>
                <td>${email.recipient}</td>
                <td>${email.subject}</td>
                <td>${getContentTypeBadge(email.content_type)}</td>
                <td>${getStatusBadge(email.status)}</td>
                <td>${getDeliveryBadge(email.delivery_status)}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Failed to load recent emails:', error);
        showError('recent-emails-body', 'Fehler beim Laden der Emails');
    }
}

// Load scheduler status
async function loadSchedulerStatus() {
    try {
        const status = await apiRequest('/api/scheduler/status');

        const statusDiv = document.getElementById('scheduler-status');
        const statusBadge = status.running
            ? '<span class="badge bg-success">Läuft</span>'
            : '<span class="badge bg-danger">Gestoppt</span>';

        let html = `<p><strong>Status:</strong> ${statusBadge}</p>`;

        if (status.jobs && status.jobs.length > 0) {
            html += '<h6>Geplante Jobs:</h6><ul class="list-unstyled">';
            status.jobs.forEach(job => {
                const nextRun = job.next_run ? formatDateTime(job.next_run) : 'Nicht geplant';
                html += `<li><i class="bi bi-clock"></i> <strong>${job.name}:</strong> ${nextRun}</li>`;
            });
            html += '</ul>';
        }

        statusDiv.innerHTML = html;

    } catch (error) {
        console.error('Failed to load scheduler status:', error);
        showError('scheduler-status', 'Fehler beim Laden des Scheduler-Status');
    }
}

// Manual send batch
async function sendManualBatch() {
    const count = prompt('Wie viele Emails sollen gesendet werden?', '5');
    if (!count) return;

    const numCount = parseInt(count);
    if (isNaN(numCount) || numCount < 1) {
        showAlert('Bitte geben Sie eine gültige Anzahl ein', 'warning');
        return;
    }

    try {
        showAlert('Sende Emails...', 'info');

        const result = await apiRequest('/emails/api/send-manual', {
            method: 'POST',
            body: JSON.stringify({ count: numCount })
        });

        if (result.success) {
            showAlert(`${result.sent_count} von ${result.total_count} Emails erfolgreich gesendet!`, 'success');
            // Reload dashboard
            setTimeout(loadDashboard, 2000);
        } else {
            showAlert('Fehler beim Senden: ' + result.error, 'danger');
        }

    } catch (error) {
        showAlert('Fehler beim Senden der Emails', 'danger');
    }
}

// Check pending emails
async function checkPendingEmails() {
    try {
        showAlert('Prüfe Emails...', 'info');

        const result = await apiRequest('/emails/api/check-pending', {
            method: 'POST'
        });

        showAlert(`${result.checked} Emails geprüft`, 'success');
        // Reload dashboard
        setTimeout(loadDashboard, 2000);

    } catch (error) {
        showAlert('Fehler beim Prüfen der Emails', 'danger');
    }
}

// Auto-refresh every 30 seconds
setInterval(loadDashboard, 30000);

// Initial load
document.addEventListener('DOMContentLoaded', loadDashboard);
