/* ============================================================
   index.js — главная страница: список конкурсов + создание
   ============================================================ */

let currentFilter = 'all';
let currentSort = '';
let currentPage = 1;

document.addEventListener('DOMContentLoaded', () => {
    setupFilters();
    loadContests();
    renderCreateButton();
});

function renderCreateButton() {
    const container = document.querySelector('.container > div:first-child');
    if (!container) return;

    const btn = document.createElement('button');
    btn.className = 'btn btn-primary';
    btn.style.cssText = 'margin-top: 20px;';
    btn.innerHTML = '➕ Создать конкурс';

    btn.onclick = () => {
        if (!API.isAuthed()) {
            toast('Войдите, чтобы создать конкурс', 'error');
            window.location.href = '/login/';
            return;
        }

        const role = API.user()?.role_id;
        if (role !== 3 && role !== 4) {
            toast('Для создания конкурса необходима роль организатора. Обратитесь к администратору.', 'error');
            return;
        }

        openModal('modal-create-contest');
    };

    container.appendChild(btn);
}

function setupFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            currentPage = 1;
            loadContests();
        });
    });

    document.getElementById('sort-select').addEventListener('change', (e) => {
        currentSort = e.target.value;
        currentPage = 1;
        loadContests();
    });
}

async function loadContests() {
    const grid = document.getElementById('contests-grid');
    const loader = document.getElementById('contests-loader');
    const empty = document.getElementById('contests-empty');

    grid.innerHTML = '';
    loader.style.display = 'block';
    empty.style.display = 'none';

    let url = `/api/contests/?filter=${currentFilter}&page=${currentPage}&per_page=9`;
    if (currentSort) url += `&sort=${currentSort}`;

    try {
        const res = await fetch(url);
        const json = await res.json();

        loader.style.display = 'none';

        if (!json.data || json.data.length === 0) {
            empty.style.display = 'block';
            return;
        }

        json.data.forEach((contest, index) => {
            const card = createContestCard(contest, index);
            grid.appendChild(card);
        });
    } catch (e) {
        loader.style.display = 'none';
        grid.innerHTML = '<p style="color: var(--danger); text-align: center; grid-column: 1/-1;">Ошибка загрузки конкурсов</p>';
    }
}

function createContestCard(contest, index) {
    const card = document.createElement('div');
    card.className = 'work-card animate-card';
    card.style.animationDelay = `${index * 0.05}s`;

    const statusMap = {
        'draft': { text: 'Черновик', class: 'badge-draft' },
        'open': { text: 'Приём работ', class: 'badge-open' },
        'voting': { text: 'Голосование', class: 'badge-voting' },
        'closed': { text: 'Завершён', class: 'badge-closed' }
    };
    const status = statusMap[contest.status] || statusMap['draft'];

    card.innerHTML = `
        <div style="padding: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <span class="badge ${status.class}">${status.text}</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">
                    ${contest.created_at ? contest.created_at.split(' ')[0] : ''}
                </span>
            </div>
            <h3 style="font-size: 1.25rem; margin-bottom: 10px; color: var(--text-primary);">
                ${esc(contest.title)}
            </h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6; margin-bottom: 20px; min-height: 60px;">
                ${esc(contest.description || 'Описание отсутствует')}
            </p>
            <a href="/contest/?id=${contest.id}" class="btn btn-primary btn-block">
                Открыть конкурс →
            </a>
        </div>
    `;

    return card;
}

// Создание конкурса
async function handleCreateContest(e) {
    e.preventDefault();
    const errBox = document.getElementById('create-contest-error');
    errBox.classList.remove('visible');
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Создание...';

    const formData = new URLSearchParams();
    formData.append('title', e.target.title.value.trim());
    formData.append('description', e.target.description.value.trim());

    try {
        const token = API.token();
        const res = await fetch('/api/contests/', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData.toString()
        });
        const data = await res.json();

        if (res.ok && data.code === 201) {
            toast('Конкурс создан!', 'success');
            closeModal('modal-create-contest');
            e.target.reset();
            loadContests();
        } else {
            errBox.textContent = data.message || 'Ошибка создания';
            errBox.classList.add('visible');
        }
    } catch (err) {
        errBox.textContent = 'Ошибка сети';
        errBox.classList.add('visible');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Создать';
    }
}

document.addEventListener('submit', (e) => {
    if (e.target.id === 'create-contest-form') {
        handleCreateContest(e);
    }
});