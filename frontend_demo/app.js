/**
 * HeroWizzard - Frontend JavaScript
 * API client and shared utilities
 */

const API_BASE = 'http://localhost:8000/api/v1';

// Token storage
const auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },

    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    setTokens(access, refresh) {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    },

    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },

    setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    },

    clear() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },

    isAuthenticated() {
        return !!this.getToken();
    }
};

// API client
const api = {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add auth token if available
        const token = auth.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Handle 401 - try to refresh token
            if (response.status === 401 && auth.getRefreshToken()) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry request with new token
                    headers['Authorization'] = `Bearer ${auth.getToken()}`;
                    const retryResponse = await fetch(url, { ...options, headers });
                    return this.handleResponse(retryResponse);
                } else {
                    auth.clear();
                    window.location.href = 'index.html';
                    return null;
                }
            }

            return this.handleResponse(response);
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async handleResponse(response) {
        const data = await response.json().catch(() => null);

        if (!response.ok) {
            const error = new Error(data?.detail || data?.error || 'API request failed');
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    },

    async refreshToken() {
        try {
            const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: auth.getRefreshToken() })
            });

            if (response.ok) {
                const data = await response.json();
                auth.setTokens(data.access, auth.getRefreshToken());
                return true;
            }
            return false;
        } catch {
            return false;
        }
    },

    // Auth endpoints
    async login(email, password) {
        const data = await this.request('/auth/token/', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        auth.setTokens(data.access, data.refresh);
        if (data.user) {
            auth.setUser(data.user);
        }

        return data;
    },

    async logout() {
        try {
            await this.request('/auth/logout/', {
                method: 'POST',
                body: JSON.stringify({ refresh: auth.getRefreshToken() })
            });
        } catch {
            // Ignore errors
        }
        auth.clear();
    },

    async getCurrentUser() {
        return this.request('/auth/me/');
    },

    // Transactions
    async getTransactions(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = `/transactions/${queryString ? '?' + queryString : ''}`;
        return this.request(endpoint);
    },

    async getTransaction(id) {
        return this.request(`/transactions/${id}/`);
    },

    async updateTransaction(id, data) {
        return this.request(`/transactions/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async getTransactionStats() {
        return this.request('/transactions/stats/');
    },

    // Import
    async uploadCSV(file) {
        const formData = new FormData();
        formData.append('file', file);

        const token = auth.getToken();
        const response = await fetch(`${API_BASE}/imports/upload/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        return this.handleResponse(response);
    },

    async getImportBatches() {
        return this.request('/imports/');
    },

    async uploadIDokladCSV(file) {
        const formData = new FormData();
        formData.append('file', file);

        const token = auth.getToken();
        const response = await fetch(`${API_BASE}/imports/upload-idoklad/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        return this.handleResponse(response);
    },

    // Category Rules
    async getCategoryRules() {
        return this.request('/category-rules/');
    },

    async createCategoryRule(data) {
        return this.request('/category-rules/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateCategoryRule(id, data) {
        return this.request(`/category-rules/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async deleteCategoryRule(id) {
        return this.request(`/category-rules/${id}/`, {
            method: 'DELETE'
        });
    },

    async applyRulesToUncategorized() {
        return this.request('/category-rules/apply_to_uncategorized/', {
            method: 'POST'
        });
    },

    // Lookups
    async getProjects() {
        return this.request('/projects/');
    },

    async getProducts() {
        return this.request('/products/');
    },

    async getSubgroups(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/subgroups/${queryString ? '?' + queryString : ''}`);
    },

    async createTransaction(data) {
        return this.request('/transactions/create-manual/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Utility functions
const utils = {
    formatCurrency(amount, currency = 'CZK') {
        const num = parseFloat(amount);
        return new Intl.NumberFormat('cs-CZ', {
            style: 'currency',
            currency: currency
        }).format(num);
    },

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('cs-CZ');
    },

    formatDateTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('cs-CZ');
    },

    getStatusBadge(status) {
        const badges = {
            'importovano': '<span class="badge badge-info">Importováno</span>',
            'zpracovano': '<span class="badge badge-warning">Zpracováno</span>',
            'schvaleno': '<span class="badge badge-success">Schváleno</span>',
            'upraveno': '<span class="badge badge-gray">Upraveno</span>',
            'chyba': '<span class="badge badge-danger">Chyba</span>'
        };
        return badges[status] || `<span class="badge badge-gray">${status}</span>`;
    },

    getPVBadge(pv) {
        if (pv === 'P') {
            return '<span class="badge badge-success">Příjem</span>';
        } else if (pv === 'V') {
            return '<span class="badge badge-danger">Výdaj</span>';
        }
        return '-';
    },

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    showAlert(container, message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        container.insertBefore(alert, container.firstChild);

        setTimeout(() => alert.remove(), 5000);
    },

    showLoading() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.id = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(overlay);
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.remove();
    }
};

// Environment detection
function getEnvironment() {
    const host = window.location.hostname;
    const port = window.location.port;
    if (host.startsWith('app.') || host === 'misehero.cz' || port === '9090') return 'production';
    if (host.startsWith('stage.') || port === '8080') return 'stage';
    return 'test';
}

function setupEnvironmentBadge() {
    const env = getEnvironment();
    const titleEl = document.getElementById('app-title');
    if (!titleEl) return;

    const colors = { test: '#e74c3c', stage: '#f39c12', production: '#27ae60' };
    const labels = { test: 'TEST', stage: 'STAGE', production: 'PROD' };

    const badge = document.createElement('span');
    badge.textContent = labels[env];
    badge.style.cssText = `
        font-size: 0.45em; padding: 2px 8px; border-radius: 4px; margin-left: 8px;
        vertical-align: middle; color: white; background: ${colors[env]};
        font-weight: 600; letter-spacing: 0.5px;
    `;
    titleEl.appendChild(badge);

    // Version and deployment date
    const versionInfo = document.createElement('span');
    versionInfo.textContent = 'v3 | 09.02.2026';
    versionInfo.style.cssText = `
        font-size: 0.35em; padding: 2px 6px; margin-left: 6px;
        vertical-align: middle; color: #6b7280; font-weight: 400;
    `;
    titleEl.appendChild(versionInfo);

    document.title = document.title + ` [${labels[env]}]`;
}

// Auto-run on every page
document.addEventListener('DOMContentLoaded', setupEnvironmentBadge);

// Check authentication on protected pages
function requireAuth() {
    if (!auth.isAuthenticated()) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// Setup navbar with user info
function setupNavbar() {
    const user = auth.getUser();
    const userInfoEl = document.getElementById('user-info');
    const logoutBtn = document.getElementById('logout-btn');

    if (userInfoEl && user) {
        userInfoEl.textContent = user.email || 'User';

        // Add role badge
        const role = user.role || '';
        if (role) {
            const roleColors = {
                admin: '#e74c3c',
                manager: '#2563eb',
                accountant: '#f59e0b',
                viewer: '#6b7280'
            };
            const roleLabels = {
                admin: 'ADMIN',
                manager: 'MANAGER',
                accountant: 'ACCOUNTANT',
                viewer: 'VIEWER'
            };
            const roleBadge = document.createElement('span');
            roleBadge.textContent = roleLabels[role] || role.toUpperCase();
            roleBadge.style.cssText = `
                font-size: 0.7em; padding: 2px 6px; border-radius: 3px;
                margin-right: 8px; color: white; font-weight: 600;
                background: ${roleColors[role] || '#6b7280'};
                letter-spacing: 0.5px;
            `;
            userInfoEl.parentNode.insertBefore(roleBadge, userInfoEl);
        }
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await api.logout();
            window.location.href = 'index.html';
        });
    }

    // Highlight active nav link
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.navbar nav a').forEach(link => {
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}
