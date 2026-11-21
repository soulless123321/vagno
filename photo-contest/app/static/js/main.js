/* ============================================================
   main.js — главная страница: список конкурсов, фильтры, пагинация
   Зависимости: api.js (API, toast, esc, renderHeader)
   ============================================================ */

const state = {
    filter: 'all',
    sort: '',
    page: 1,
    perPage: 9,
};

// Красивые картинки-заглушки (в БД нет обложки конкурса)
const fallbackImages = [
    'https://images.unsplash.com/photo-1483347756197-71ef80e95f73?auto=format&fit=crop&w=500&q=80', // Сияние
    'https://images.unsplash.com/photo-1517404215738-15263e9f9178?auto=format&fit=crop&w=500&q=80', // Горы
    'https://images.unsplash.com/photo-1478719059408-592965723cbc?auto=format&fit=crop&w=500&q=80', // Зима
    'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=500&q=80', // Снег
    'https://images.unsplash.com/photo-1520763185298-1b434c919102?auto=format&fit=crop&w=500&q=80'  // Лес
];

const STATUS_MAP = {
    open:   { text: 'Приём работ', cls: 'badge-open' },
    voting: { text: 'Голосование', cls: 'badge-voting' },
    closed: { text: 'Завершён',    cls: 'badge-closed' },
    draft:  { text: 'Черновик',    cls: 'badge-draft' },
};

async function loadContests() {
    const grid = document.getElementById('contests-grid');
    const loader = document.getElementById('loader');
    const errorMsg = document.getElementById('error-message');
    if (!grid) return;

    loader.classList.add('visible');
    errorMsg.classList.remove('visible');
    grid.innerHTML = '';

    const params = new URLSearchParams({
        page: state.page,
        per_page: state.perPage,
        filter: state.filter,
    });
    if (state.sort) params.set('sort', state.sort);

    // Для фильтра "mine" токен обязателен
    const { ok, status, data } = await API.getJSON(`/api/contests/?${params}`, true);

    loader.classList.remove('visible');

    if (!ok) {
        if (status === 401 && state.filter === 'mine') {
            errorMsg.textContent = 'Войдите, чтобы увидеть свои конкурсы.';
        } else {
            errorMsg.textContent = 'Не удалось загрузить конкурсы. Проверьте, запущен ли сервер.';
        }
        errorMsg.classList.add('visible');
        return;
    }

    const contests = data?.data || [];
    renderContestCards(contests);
    renderPagination(data?.meta?.page ?? state.page);
}

function renderContestCards(contests) {
    const grid = document.getElementById('contests-grid');

    if (contests.length === 0) {
        grid.innerHTML = '<p class="empty-state">Пока нет конкурсов в этой категории. Загляните позже!</p>';
        return;
    }

    contests.forEach((contest, index) => {
        const card = document.createElement('div');
        card.className = 'card animate-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const title = contest.title || 'Без названия';
        const description = contest.description || 'Описание пока не добавлено.';
        const st = STATUS_MAP[(contest.status || 'draft').toLowerCase()] || STATUS_MAP.draft;
        const imageUrl = fallbackImages[index % fallbackImages.length];
        const created = contest.created_at ? `Создан: ${esc(String(contest.created_at).slice(0, 10))}` : '';

        card.innerHTML = `
            <div class="card-img-wrapper">
                <img src="${imageUrl}" alt="${esc(title)}" class="card-img" loading="lazy">
                <span class="badge ${st.cls} badge-float">${st.text}</span>
            </div>
            <div class="card-body">
                <h3 class="card-title">${esc(title)}</h3>
                <p class="card-text">${esc(description)}</p>
                <div class="card-meta">${created}</div>
                <a href="/contest/?id=${contest.id}" class="btn card-btn">Подробнее</a>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderPagination(page) {
    const box = document.getElementById('pagination');
    const info = document.getElementById('page-info');
    const prev = document.getElementById('page-prev');
    const next = document.getElementById('page-next');
    if (!box) return;

    box.style.display = 'flex';
    info.textContent = `Страница ${page}`;
    prev.disabled = page <= 1;
    // total_pages бэкенд не возвращает — даём идти вперёд; пустая страница покажет "нет конкурсов"
    next.disabled = false;
}

document.addEventListener('DOMContentLoaded', () => {
    // Фильтры-чипы
    document.querySelectorAll('.chip[data-filter]').forEach(chip => {
        chip.addEventListener('click', () => {
            const f = chip.dataset.filter;
            if (f === 'mine' && !API.isAuthed()) {
                toast('Сначала войдите в аккаунт', 'error');
                openModal('modal-register');
                return;
            }
            document.querySelectorAll('.chip[data-filter]').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            state.filter = f;
            state.page = 1;
            loadContests();
        });
    });

    // Сортировка
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) sortSelect.addEventListener('change', () => {
        state.sort = sortSelect.value;
        state.page = 1;
        loadContests();
    });

    // Пагинация
    document.getElementById('page-prev')?.addEventListener('click', () => {
        if (state.page > 1) { state.page--; loadContests(); }
    });
    document.getElementById('page-next')?.addEventListener('click', () => {
        state.page++; loadContests();
    });

    loadContests();
});
