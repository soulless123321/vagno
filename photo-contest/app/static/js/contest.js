/* ============================================================
   contest.js — страница конкурса: инфо, галерея работ,
   загрузка своей работы, голосование (UI)
   Зависимости: api.js
   ============================================================ */

let CONTEST_ID = null;
let currentContest = null;
// Работы, за которые пользователь уже голосовал (per-browser)
const myVotesKey = () => `my_votes_${API.user()?.id ?? 'anon'}`;
const getMyVotes = () => { try { return JSON.parse(localStorage.getItem(myVotesKey())) || {}; } catch { return {}; } };
const setMyVote = (contestId, workId) => { const v = getMyVotes(); v[contestId] = workId; localStorage.setItem(myVotesKey(), JSON.stringify(v)); };
const getMyVote = (contestId) => getMyVotes()[contestId] || null;

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    CONTEST_ID = urlParams.get('id');

    if (!CONTEST_ID) {
        toast('Конкурс не найден!', 'error');
        window.location.href = '/';
        return;
    }

    loadContestData(CONTEST_ID);
    setupUploadForm(CONTEST_ID);
});

// 1. Данные конкурса (бэкенд не отдаёт один конкурс — берём список и ищем)
async function loadContestData(id) {
    const { ok, data } = await API.getJSON('/api/contests/?per_page=100&page=1', true);

    if (!ok) {
        document.getElementById('contest-title').textContent = 'Не удалось загрузить конкурс';
        document.getElementById('contest-status').textContent = 'Ошибка';
        return;
    }

    const contest = (data?.data || []).find(c => c.id == id);
    if (!contest) {
        document.getElementById('contest-title').textContent = 'Конкурс не найден';
        document.getElementById('contest-status').textContent = 'Нет such';
        document.getElementById('contest-status').className = 'badge badge-closed';
        return;
    }

    currentContest = contest;
    document.getElementById('contest-title').textContent = contest.title || 'Без названия';
    document.getElementById('contest-desc').textContent = contest.description || 'Описание отсутствует';

    const statusBadge = document.getElementById('contest-status');
    const status = (contest.status || 'draft').toLowerCase();

    if (status === 'open') {
        statusBadge.textContent = 'Прием работ';
        statusBadge.className = 'badge badge-open';
    } else if (status === 'voting') {
        statusBadge.textContent = 'Голосование';
        statusBadge.className = 'badge badge-voting';
    } else if (status === 'closed') {
        statusBadge.textContent = 'Завершен';
        statusBadge.className = 'badge badge-closed';
    } else {
        statusBadge.textContent = 'Черновик';
        statusBadge.className = 'badge badge-draft';
    }

    // Форма участия: показываем если приём работ И пользователь вошёл
    const uploadBox = document.getElementById('upload-container');
    if (status === 'open') {
        if (API.isAuthed()) {
            uploadBox.style.display = 'block';
        } else {
            uploadBox.style.display = 'block';
            uploadBox.innerHTML = `
                <h3>Хотите участвовать?</h3>
                <p class="contest-desc" style="margin: 0 auto 20px;">Войдите в аккаунт, чтобы загрузить свою работу в этот конкурс.</p>
                <a href="/login/" class="btn">Войти</a>
            `;
        }
    }

    if (status === 'voting') {
        document.getElementById('vote-hint').style.display = 'flex';
    }

    loadWorks(id);
}

// 2. Галерея работ
async function loadWorks(id) {
    const gallery = document.getElementById('works-gallery');
    const loader = document.getElementById('loader');
    const galleryTitle = document.getElementById('gallery-title');

    loader.classList.add('visible');
    gallery.innerHTML = '';

    const { ok, data } = await API.getJSON(`/api/works/?contest_id=${id}`);
    loader.classList.remove('visible');
    galleryTitle.style.display = 'block';

    if (!ok) {
        gallery.innerHTML = '<p style="color: #ef4444;">Не удалось загрузить работы.</p>';
        return;
    }

    const works = data?.data || [];

    if (works.length === 0) {
        gallery.innerHTML = '<p class="empty-state">Пока нет загруженных работ. Станьте первым!</p>';
        return;
    }

    const votedWorkId = getMyVote(id);

    works.forEach(work => {
        const card = document.createElement('div');
        card.className = 'work-card animate-card';

        const imageUrl = String(work.image).startsWith('http') ? work.image : `/media/${work.image}`;
        const isVoted = votedWorkId && votedWorkId == work.id;
        const votingOpen = currentContest && (currentContest.status === 'voting' || currentContest.status === 'closed');
        const isOwn = API.isAuthed() && API.user()?.id === work.user_id;

        let voteBtnHtml = '';
        if (votingOpen) {
            if (isVoted) {
                voteBtnHtml = `<button class="vote-btn" disabled>✔ Ваш голос учтён</button>`;
            } else if (isOwn) {
                voteBtnHtml = `<button class="vote-btn" disabled title="Нельзя голосовать за свою работу">Это ваша работа</button>`;
            } else {
                voteBtnHtml = `<button class="vote-btn" data-work-id="${work.id}">👍 Голосовать</button>`;
            }
        }

        card.innerHTML = `
            <img src="${imageUrl}" alt="${esc(work.title)}" class="work-img" loading="lazy">
            <div class="work-info">
                <h3 class="work-title">${esc(work.title)}</h3>
                <p class="work-author">Автор ID: ${esc(work.user_id ?? '?')}</p>
                ${voteBtnHtml}
                <div class="vote-count">Голосов: <span class="votes-num">${work.votes_count || 0}</span></div>
            </div>
        `;
        gallery.appendChild(card);
    });

    // Обработчики кнопок голосования
    gallery.querySelectorAll('.vote-btn[data-work-id]').forEach(btn => {
        btn.addEventListener('click', () => castVote(btn, id));
    });
}

// 3. Голосование.
// ВНИМАНИЕ: на бэкенде пока нет эндпоинта POST /api/votes/ —
// поэтому голос сохраняется локально, а кнопка блокируется.
// Когда появится API — замените тело функции на fetch-запрос.
async function castVote(btn, contestId) {
    if (!API.isAuthed()) {
        toast('Войдите, чтобы голосовать', 'error');
        openModal('modal-register');
        return;
    }

    const workId = btn.dataset.workId;
    setMyVote(contestId, Number(workId));

    // Обновляем UI: снимаем выделение с других кнопок, ставим галочку этой
    const gallery = document.getElementById('works-gallery');
    gallery.querySelectorAll('.vote-btn[data-work-id]').forEach(b => {
        b.textContent = '👍 Голосовать';
    });
    btn.textContent = '✔ Ваш голос учтён';
    btn.disabled = true;

    const countEl = btn.closest('.work-info').querySelector('.votes-num');
    if (countEl) countEl.textContent = Number(countEl.textContent || 0) + 1;

    toast('Голос принят! (локально — до подключения API голосования)', 'success');
}

// 4. Форма загрузки работы
function setupUploadForm(contestId) {
    const form = document.getElementById('upload-form');
    if (!form) return; // блок мог быть заменён на "Войдите"

    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadArea = document.getElementById('upload-area');
    const preview = document.getElementById('upload-preview');
    const errBox = document.getElementById('upload-error');
    const submitBtn = document.getElementById('upload-btn');

    const showFile = (file) => {
        fileNameDisplay.innerHTML = `✅ Выбран файл: <b>${esc(file.name)}</b> (${(file.size / 1024 / 1024).toFixed(2)} МБ)`;
        uploadArea.style.borderColor = 'var(--accent)';
        const url = URL.createObjectURL(file);
        preview.src = url;
        preview.style.display = 'block';
    };

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) showFile(fileInput.files[0]);
    });

    // Drag and Drop
    ['dragover'].forEach(ev => uploadArea.addEventListener(ev, (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach(ev => uploadArea.addEventListener(ev, (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    }));
    uploadArea.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            showFile(e.dataTransfer.files[0]);
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errBox.classList.remove('visible');

        if (!API.token()) {
            toast('Вы должны войти, чтобы загрузить работу!', 'error');
            window.location.href = '/login/';
            return;
        }

        const title = document.getElementById('work-title').value.trim();
        const file = fileInput.files[0];

        if (!title) { errBox.textContent = 'Введите название работы'; errBox.classList.add('visible'); return; }
        if (!file) { errBox.textContent = 'Выберите файл!'; errBox.classList.add('visible'); return; }
        if (file.size > 10 * 1024 * 1024) {
            errBox.textContent = 'Файл слишком большой (макс. 10 МБ)';
            errBox.classList.add('visible'); return;
        }

        const formData = new FormData();
        formData.append('title', title);
        formData.append('image', file);
        formData.append('contest_id', contestId);

        submitBtn.disabled = true;
        submitBtn.textContent = 'Загрузка...';

        const { ok, data } = await API.postMultipart('/api/works/', formData);

        submitBtn.disabled = false;
        submitBtn.textContent = 'Загрузить работу';

        if (!ok) {
            if (data?.message?.toLowerCase?.().includes('токен')) {
                API.clearSession();
                toast('Сессия истекла — войдите снова', 'error');
                setTimeout(() => location.href = '/login/', 1200);
                return;
            }
            errBox.textContent = data?.message || 'Ошибка при загрузке работы';
            errBox.classList.add('visible');
            return;
        }

        toast('Работа загружена и отправлена на модерацию!', 'success');
        form.reset();
        preview.style.display = 'none';
        fileNameDisplay.innerHTML = '📷 Нажмите, чтобы выбрать фото, или перетащите файл сюда<br><small>JPEG / PNG / WEBP, макс. 10 МБ</small>';
        uploadArea.style.borderColor = 'var(--border-color)';
        // На модерации — в галерее её пока не видно, но обновим на всякий случай
        loadWorks(contestId);
    });
}
