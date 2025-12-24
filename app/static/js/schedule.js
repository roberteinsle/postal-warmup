// Schedule Page JavaScript

let scheduleData = [];
let editingScheduleId = null;

// Load schedule
async function loadSchedule() {
    try {
        scheduleData = await apiRequest('/schedule/api/list');

        const tbody = document.getElementById('schedule-table-body');
        if (scheduleData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Kein Schedule vorhanden</td></tr>';
            return;
        }

        tbody.innerHTML = scheduleData.map(schedule => {
            const lastExecution = schedule.execution_history.length > 0
                ? `${formatDate(schedule.execution_history[0].date)} (${schedule.execution_history[0].sent_count} gesendet)`
                : 'Noch nicht ausgeführt';

            const statusBadge = schedule.enabled
                ? '<span class="badge bg-success">Aktiv</span>'
                : '<span class="badge bg-secondary">Inaktiv</span>';

            return `
                <tr>
                    <td><strong>Tag ${schedule.day}</strong></td>
                    <td>
                        <input type="number" class="form-control form-control-sm"
                               value="${schedule.target_emails}"
                               min="0"
                               onchange="markChanged(${schedule.id}, 'target_emails', this.value)"
                               style="width: 100px;">
                    </td>
                    <td>
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox"
                                   ${schedule.enabled ? 'checked' : ''}
                                   onchange="markChanged(${schedule.id}, 'enabled', this.checked)">
                        </div>
                    </td>
                    <td>${lastExecution}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editSchedule(${schedule.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Failed to load schedule:', error);
        showError('schedule-table-body', 'Fehler beim Laden des Schedules');
    }
}

// Mark schedule as changed
let changedSchedules = new Set();

function markChanged(scheduleId, field, value) {
    const schedule = scheduleData.find(s => s.id === scheduleId);
    if (schedule) {
        if (field === 'target_emails') {
            schedule.target_emails = parseInt(value);
        } else if (field === 'enabled') {
            schedule.enabled = value;
        }
        changedSchedules.add(scheduleId);
    }
}

// Save all changes
async function saveAllChanges() {
    if (changedSchedules.size === 0) {
        showAlert('Keine Änderungen zum Speichern', 'info');
        return;
    }

    try {
        const updates = Array.from(changedSchedules).map(id => {
            const schedule = scheduleData.find(s => s.id === id);
            return {
                id: schedule.id,
                target_emails: schedule.target_emails,
                enabled: schedule.enabled
            };
        });

        const result = await apiRequest('/schedule/api/bulk-update', {
            method: 'POST',
            body: JSON.stringify({ schedules: updates })
        });

        showAlert(`${result.updated} Schedule-Tage erfolgreich aktualisiert!`, 'success');
        changedSchedules.clear();

        // Reload schedule
        await loadSchedule();

    } catch (error) {
        showAlert('Fehler beim Speichern der Änderungen', 'danger');
    }
}

// Edit schedule (modal)
function editSchedule(scheduleId) {
    const schedule = scheduleData.find(s => s.id === scheduleId);
    if (!schedule) return;

    editingScheduleId = scheduleId;

    document.getElementById('modal-day').textContent = schedule.day;
    document.getElementById('modal-target-emails').value = schedule.target_emails;
    document.getElementById('modal-enabled').checked = schedule.enabled;

    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
}

// Save schedule day
async function saveScheduleDay() {
    if (!editingScheduleId) return;

    try {
        const targetEmails = parseInt(document.getElementById('modal-target-emails').value);
        const enabled = document.getElementById('modal-enabled').checked;

        await apiRequest(`/schedule/api/${editingScheduleId}`, {
            method: 'PUT',
            body: JSON.stringify({
                target_emails: targetEmails,
                enabled: enabled
            })
        });

        showAlert('Schedule erfolgreich aktualisiert!', 'success');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
        modal.hide();

        // Reload schedule
        await loadSchedule();

    } catch (error) {
        showAlert('Fehler beim Speichern des Schedules', 'danger');
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', loadSchedule);
