/* ============================================================
   api.js — общий модуль: авторизация, шапка, toast, модалки
   ============================================================ */

const API = {
    token: () => localStorage.getItem('auth_token'),
    user: () => {
        try { return JSON.parse(localStorage.getItem('auth_user')); }
        catch { return null; }
    },
    setSession: (token, user) => {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(user));
    },
    clearSession: () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
    },
    isAuthed: () => !!API.token(),

    postForm: async (url, fields = {}, withAuth = false) => {
        const body = new URLSearchParams();
        Object.entries(fields).forEach(([k, v]) => body.append(k, v));
        const headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
        if (withAuth && API.token()) headers['Authorization'] = `Bearer ${API.token()}`;
        const res = await fetch(url, { method: 'POST', headers, body: body.toString() });
        let data = null;
        try { data = await res.json(); } catch {}
        return { ok: res.ok, status: res.status, data };
    },

    postMultipart: async (url, formData, withAuth = true) => {
        const headers = {};
        if (withAuth && API.token()) headers['Authorization'] = `Bearer ${API.token()}`;
        const res = await fetch(url, { method: 'POST', headers, body: formData });
        let data = null;
        try { data = await res.json(); } catch {}
        return { ok: res.ok, status: res.status, data };
    },

    getJSON: async (url, withAuth = false) => {
        const headers = { 'Content-Type': 'application/json' };
        if (withAuth && API.token()) headers['Authorization'] = `Bearer ${API.token()}`;
        const res = await fetch(url, { headers });
        let data = null;
        try { data = await res.json(); } catch {}
        return { ok: res.ok, status: res.status, data };
    },
};

// ---------- Toast ----------
function toast(message, type = 'info', ms = 3500) {
    let box = document.getElementById('toast-container');
    if (!box) {
        box = document.createElement('div');
        box.id = 'toast-container';
        document.body.appendChild(box);
    }
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    box.appendChild(el);
    setTimeout(() => {
        el.classList.add('hide');
        setTimeout(() => el.remove(), 350);
    }, ms);
}

// ---------- Экранирование (защита от XSS) ----------
function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
}

// ---------- Права на управление ----------
function canManage() {
    const u = API.user();
    return u && (u.role_id === 3 || u.role_id === 4);
}

// ---------- Шапка ----------
function renderHeader() {
    const nav = document.getElementById('nav-auth-area');
    if (!nav) return;
    const user = API.user();

    if (API.isAuthed() && user) {
        nav.innerHTML = `
            <span class="nav-user">Привет, <b>${esc(user.name)}</b></span>
            <a href="/profile/" class="btn btn-outline btn-sm">Профиль</a>
            ${canManage() ? `<button class="btn btn-sm" id="btn-create-contest">+ Конкурс</button>` : ''}
            <button class="btn btn-outline btn-sm" id="btn-logout">Выйти</button>
        `;
        document.getElementById('btn-logout').addEventListener('click', logout);
        const createBtn = document.getElementById('btn-create-contest');
        if (createBtn) createBtn.addEventListener('click', () => openModal('modal-create-contest'));
    } else {
        nav.innerHTML = `
            <a href="/login/" class="btn btn-outline btn-sm">Войти</a>
            <button class="btn btn-sm" id="btn-register-open">Регистрация</button>
        `;
        document.getElementById('btn-register-open').addEventListener('click', () => openModal('modal-register'));
    }
}

async function logout() {
    try { await API.postForm('/api/logout/', {}, true); } catch {}
    API.clearSession();
    toast('Вы вышли из системы', 'success');
    renderHeader();
    if (location.pathname !== '/') window.location.href = '/';
}

// ---------- Модальные окна ----------
function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('open');
}
function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('open');
}
function setupModals() {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.remove('open');
        });
    });
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => btn.closest('.modal-overlay').classList.remove('open'));
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape')
            document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    });
}

// ---------- Форма регистрации ----------
function setupRegisterForm() {
    const form = document.getElementById('register-form');
    if (!form) return;
    const errBox = document.getElementById('register-error');
    const successBox = document.getElementById('register-success');
    const btn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        btn.disabled = true; btn.textContent = 'Отправка...';

        ['name', 'email', 'password'].forEach(f => {
            const fe = document.getElementById(`reg-fe-${f}`);
            const inp = document.getElementById(`reg-${f}`);
            if (fe) { fe.classList.remove('visible'); fe.textContent = ''; }
            if (inp) inp.classList.remove('invalid');
        });
        errBox.classList.remove('visible');
        successBox.classList.remove('visible');

        const fields = {
            name: document.getElementById('reg-name').value.trim(),
            email: document.getElementById('reg-email').value.trim(),
            password: document.getElementById('reg-password').value,
        };

        const { ok, status, data } = await API.postForm('/api/users/', fields);
        btn.disabled = false; btn.textContent = 'Зарегистрироваться';

        if (ok) {
            form.reset();
            errBox.classList.remove('visible');
            successBox.classList.add('visible');
            return;
        }

        const errors = data?.errors || {};
        ['name', 'email', 'password'].forEach(f => {
            const fe = document.getElementById(`reg-fe-${f}`);
            const inp = document.getElementById(`reg-${f}`);
            if (errors[f] && fe && inp) {
                fe.textContent = errors[f].join(', ');
                fe.classList.add('visible');
                inp.classList.add('invalid');
            }
        });
        if (!Object.keys(errors).length) {
            errBox.textContent = data?.message || 'Ошибка регистрации';
            errBox.classList.add('visible');
        }
    });
}

// ---------- Форма создания конкурса ----------
function setupCreateContestForm() {
    const form = document.getElementById('create-contest-form');
    if (!form) return;
    const errBox = document.getElementById('contest-error');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true; btn.textContent = 'Создание...';
        errBox.classList.remove('visible');

        const fields = {
            title: document.getElementById('cc-title').value.trim(),
            description: document.getElementById('cc-description').value.trim(),
        };

        const { ok, data } = await API.postForm('/api/contests/', fields, true);
        btn.disabled = false; btn.textContent = 'Создать конкурс';

        if (ok) {
            toast(`Конкурс «${data.data.title}» создан`, 'success');
            form.reset();
            closeModal('modal-create-contest');
            if (typeof loadContests === 'function') loadContests();
        } else {
            if (data?.status === 401) {
                API.clearSession();
                renderHeader();
                toast('Сессия истекла, войдите снова', 'error');
            } else if (data?.status === 403) {
                toast('Недостаточно прав для создания конкурса', 'error');
            }
            errBox.textContent = data?.message || 'Не удалось создать конкурс';
            errBox.classList.add('visible');
        }
    });
}
// Refresh token
// ---------- Refresh session (используется при истечении access-токена) ----------
API.refreshSession = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return { ok: false, status: 401 };

    const { ok, data } = await API.postForm('/api/refresh/', { token: refreshToken });
    if (ok && data?.data?.token) {
        API.setSession(data.data.token, API.user());
        localStorage.setItem('refresh_token', data.data.refresh_token);
        return { ok: true };
    }
    return { ok: false };
};

// ---------- Инициализация ----------
document.addEventListener('DOMContentLoaded', () => {
    renderHeader();
    setupModals();
    setupRegisterForm();
    setupCreateContestForm();
});