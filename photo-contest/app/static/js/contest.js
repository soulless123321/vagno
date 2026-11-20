/* ============================================================
   contest.js — страница конкурса: инфо, галерея, загрузка,
   голосование, модерация и управление статусом
   Зависимости: api.js
   ============================================================ */

let CONTEST_ID = null;
let currentContest = null;
let isModerationMode = false;

const myVotesKey = () => `my_votes_${API.user()?.id ?? 'anon'}`;
const getMyVotes = () => { try { return JSON.parse(localStorage.getItem(myVotesKey())) || {}; } catch { return {}; } };
const setMyVote = (contestId, workId) => {
    const v = getMyVotes();
    v[contestId] = workId;
    localStorage.setItem(myVotesKey(), JSON.stringify(v));
};
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

// 1. Данные конкурса
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
        document.getElementById('contest-status').textContent = 'Нет такого';
        document.getElementById('contest-status').className = 'badge badge-closed';
        return;
    }

    currentContest = contest;
    document.getElementById('contest-title').textContent = contest.title || 'Без названия';
    document.getElementById('contest-desc').textContent = contest.description || 'Описание отсутствует';

    const statusBadge = document.getElementById('contest-status');
    const status = (contest.status || 'draft').toLowerCase();

    if (status === 'open') {
        statusBadge.textContent = 'Приём работ';
        statusBadge.className = 'badge badge-open';
    } else if (status === 'voting') {
        statusBadge.textContent = 'Голосование';
        statusBadge.className = 'badge badge-voting';
    } else if (status === 'closed') {
        statusBadge.textContent = 'Завершён';
        statusBadge.className = 'badge badge-closed';
    } else {
        statusBadge.textContent = 'Черновик';
        statusBadge.className = 'badge badge-draft';
    }

    if (canManage()) {
        const statusPanel = document.getElementById('status-control-panel');
        const statusText = document.getElementById('current-status-text');
        const statusBtn = document.getElementById('btn-change-status');

        if (statusPanel && statusText && statusBtn) {
            statusPanel.style.display = 'block';
            statusText.textContent = status.toUpperCase();

            const statusActions = {
                'draft': { text: '🚀 Открыть приём работ', nextStatus: 'open' },
                'open': { text: '🗳️ Начать голосование', nextStatus: 'voting' },
                'voting': { text: '🏆 Завершить конкурс', nextStatus: 'closed' },
                'closed': null
            };

            const action = statusActions[status];
            if (action) {
                statusBtn.textContent = action.text;
                statusBtn.onclick = () => changeContestStatus(CONTEST_ID, action.nextStatus);
            } else {
                statusBtn.textContent = 'Конкурс завершён';
                statusBtn.disabled = true;
                statusBtn.style.opacity = '0.6';
            }
        }

        const modToggle = document.createElement('button');
        modToggle.className = 'btn btn-outline btn-sm';
        modToggle.style.marginTop = '15px';
        modToggle.style.marginRight = '10px';
        modToggle.textContent = '🛡 Режим модерации';
        modToggle.onclick = () => {
            isModerationMode = !isModerationMode;
            modToggle.textContent = isModerationMode ? '👁 Обычный режим' : '🛡 Режим модерации';
            modToggle.className = isModerationMode ? 'btn btn-sm' : 'btn btn-outline btn-sm';
            loadWorks(id);
        };
        document.getElementById('contest-desc').after(modToggle);
    }

    const uploadBox = document.getElementById('upload-container');
    if (status === 'open') {
        if (API.isAuthed()) {
            uploadBox.style.display = 'block';
        } else {
            uploadBox.style.display = 'block';
            uploadBox.innerHTML = `
                <h3>Хотите участвовать?</h3>
                <p class="contest-desc" style="margin: 0 auto 20px;">Войдите в аккаунт, чтобы загрузить свою работу.</p>
                <a href="/login/" class="btn">Войти</a>
            `;
        }
    }

    if (status === 'voting' && !isModerationMode) {
        document.getElementById('vote-hint').style.display = 'flex';
    }

    loadWorks(id);
}

// 2. Галерея работ
async function loadWorks(id) {
    const gallery = document.getElementById('works-gallery');
    const loader = document.getElementById('loader');
    const galleryTitle = document.getElementById('gallery-title');
    const voteHint = document.getElementById('vote-hint');

    loader.classList.add('visible');
    gallery.innerHTML = '';

    const statusParam = isModerationMode ? 'pending' : 'approved';

    const [worksResponse, voteResponse] = await Promise.all([
        API.getJSON(`/api/works/?contest_id=${id}&status=${statusParam}`),
        !isModerationMode && API.isAuthed() ? API.getJSON(`/api/votes/?contest_id=${id}`, true) : Promise.resolve({ ok: false })
    ]);

    loader.classList.remove('visible');

    if (isModerationMode) {
        galleryTitle.textContent = 'Работы, ожидающие модерации';
        voteHint.style.display = 'none';
    } else {
        galleryTitle.textContent = 'Работы участников';
        if (currentContest && currentContest.status === 'voting') {
            voteHint.style.display = 'flex';
        }
    }
    galleryTitle.style.display = 'block';

    if (!worksResponse.ok) {
        gallery.innerHTML = '<p style="color: #ef4444;">Не удалось загрузить работы.</p>';
        return;
    }

    const works = worksResponse.data?.data || [];

    if (!isModerationMode && voteResponse.ok && voteResponse.data?.data) {
        setMyVote(id, voteResponse.data.data.work_id);
    }

    if (works.length === 0) {
        const emptyMsg = isModerationMode ? 'Нет работ, ожидающих модерации. Отличная работа!' : 'Пока нет загруженных работ. Станьте первым!';
        gallery.innerHTML = `<p class="empty-state">${emptyMsg}</p>`;
        return;
    }

    const votedWorkId = !isModerationMode ? getMyVote(id) : null;

    works.forEach(work => {
        const card = document.createElement('div');
        card.className = 'work-card animate-card';
        card.dataset.workId = work.id;

        const imageUrl = String(work.image).startsWith('http') ? work.image : `/media/${work.image}`;
        const isOwn = API.isAuthed() && API.user()?.id === work.user_id;

        let actionHtml = '';

        if (isModerationMode) {
            actionHtml = `
                <div style="display:flex; gap:10px; margin-top:15px;">
                    <button class="btn btn-sm" style="background:var(--success); color:#fff; flex:1;" onclick="moderateWork(${work.id}, 'approve')">✔ Одобрить</button>
                    <button class="btn btn-sm btn-danger" style="flex:1;" onclick="moderateWork(${work.id}, 'reject')">✖ Отклонить</button>
                </div>
            `;
        } else {
            const isVoted = votedWorkId && votedWorkId == work.id;
            const votingOpen = currentContest && (currentContest.status === 'voting' || currentContest.status === 'closed');
            const hasVoted = !!votedWorkId;

            if (votingOpen) {
                if (isVoted) {
                    actionHtml = `<button class="vote-btn" disabled>✔ Ваш голос учтён</button>`;
                } else if (isOwn) {
                    actionHtml = `<button class="vote-btn" disabled title="Нельзя голосовать за свою работу">Это ваша работа</button>`;
                } else if (hasVoted) {
                    actionHtml = `<button class="vote-btn" disabled>👍 Голосовать</button>`;
                } else {
                    actionHtml = `<button class="vote-btn" data-work-id="${work.id}">👍 Голосовать</button>`;
                }
            }
        }

        card.innerHTML = `
            <img src="${imageUrl}" alt="${esc(work.title)}" class="work-img" loading="lazy">
            <div class="work-info">
                <h3 class="work-title">${esc(work.title)}</h3>
                <p class="work-author">Автор ID: ${esc(work.user_id ?? '?')}</p>
                ${actionHtml}
                ${!isModerationMode ? `<div class="vote-count">Голосов: <span class="votes-num">${work.votes_count||0}</span></div>` : ''}
                <div class="vote-count">Просмотров: <span class="views-num">${work.views||0}</span></div>
                <button class="btn btn-sm btn-outline" style="margin-top: 10px; width: 100%;" onclick="openComments(${work.id})">
                    💬 Комментарии
                </button>
            </div>
        `;
        gallery.appendChild(card);
    });

    if (!isModerationMode) {
        gallery.querySelectorAll('.vote-btn[data-work-id]').forEach(btn => {
            btn.addEventListener('click', () => castVote(btn, id));
        });
    }
    setupViewsTracking();
}

// 3. Голосование
async function castVote(btn, contestId) {
    if (!API.isAuthed()) {
        toast('Войдите, чтобы голосовать', 'error');
        openModal('modal-register');
        return;
    }

    const workId = btn.dataset.workId;
    btn.disabled = true;
    btn.textContent = 'Отправка...';

    const { ok, status, data } = await API.postForm('/api/votes/', {
        contest_id: contestId,
        work_id: workId
    }, true);

    if (!ok) {
        btn.disabled = false;
        btn.textContent = '👍 Голосовать';

        if (status === 401) {
            API.clearSession();
            renderHeader();
            toast('Сессия истекла, войдите снова', 'error');
            return;
        }
        if (status === 403) {
            toast(data?.message || 'Вы уже голосовали в этом конкурсе', 'error');
            return;
        }
        toast(data?.message || 'Ошибка при голосовании', 'error');
        return;
    }

    setMyVote(contestId, Number(workId));
    const gallery = document.getElementById('works-gallery');
    gallery.querySelectorAll('.vote-btn[data-work-id]').forEach(b => {
        if (b.dataset.workId === workId) {
            b.textContent = '✔ Ваш голос учтён';
            b.disabled = true;
        } else {
            b.disabled = true;
        }
    });

    const countEl = btn.closest('.work-info').querySelector('.votes-num');
    if (countEl && data?.data?.votes_count !== undefined) {
        countEl.textContent = data.data.votes_count;
    }
    toast('Голос принят!', 'success');
}

// 4. Модерация работы
async function moderateWork(workId, action) {
    const actionText = action === 'approve' ? 'Одобрить' : 'Отклонить';
    if (!confirm(`Вы уверены, что хотите ${actionText.toLowerCase()} эту работу?`)) return;

    const btns = document.querySelectorAll(`button[onclick="moderateWork(${workId}, '${action}')"]`);
    btns.forEach(b => { b.disabled = true; b.textContent = 'Обработка...'; });

    const { ok, data } = await API.postForm('/api/works/moderate/', {
        work_id: workId,
        action: action
    }, true);

    if (ok) {
        toast(data.message, 'success');
        loadWorks(CONTEST_ID);
    } else {
        toast(data?.message || 'Ошибка модерации', 'error');
        btns.forEach(b => {
            b.disabled = false;
            b.textContent = action === 'approve' ? '✔ Одобрить' : '✖ Отклонить';
        });
    }
}

// 5. Форма загрузки работы
function setupUploadForm(contestId) {
    const form = document.getElementById('upload-form');
    if (!form) return;

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

        const { ok, data } = await API.postMultipart('/api/works/', formData, true);

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
    });
}

// 6. Управление статусом конкурса
async function changeContestStatus(contestId, newStatus) {
    const statusNames = {
        'open': 'приём работ',
        'voting': 'голосование',
        'closed': 'завершён'
    };

    if (!confirm(`Вы уверены, что хотите перевести конкурс в статус "${statusNames[newStatus]}"?`)) {
        return;
    }

    const btn = document.getElementById('btn-change-status');
    const errBox = document.getElementById('status-error');

    btn.disabled = true;
    btn.textContent = 'Обработка...';
    errBox.classList.remove('visible');

    const { ok, data } = await API.postForm(`/api/contests/${contestId}/status/`, {
        status: newStatus
    }, true);

    btn.disabled = false;

    if (ok) {
        toast(data.message, 'success');
        setTimeout(() => window.location.reload(), 1500);
    } else {
        errBox.textContent = data?.message || 'Ошибка смены статуса';
        errBox.classList.add('visible');
        btn.textContent = 'Попробовать снова';
    }
}

// 7. Отслеживание просмотров
let viewsObserver = null;
const viewedOnce = new Set();

function setupViewsTracking() {
    if (viewsObserver) viewsObserver.disconnect();
    viewsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const card = entry.target;
                const workId = card.dataset.workId;
                if (workId && !viewedOnce.has(workId)) {
                    viewedOnce.add(workId);
                    incrementViews(workId, card);
                }
                viewsObserver.unobserve(card);
            }
        });
    }, { threshold: 0.5 });
    document.querySelectorAll('#works-gallery .work-card').forEach(card => {
        viewsObserver.observe(card);
    });
}

async function incrementViews(workId, card) {
    try {
        const res = await fetch(`/api/works/${workId}/view/`, { method: 'POST' });
        const json = await res.json();
        if (res.ok && json.code === 200) {
            const el = card.querySelector('.views-num');
            if (el) el.textContent = json.data.views;
        }
    } catch (e) {
        // тихо игнорируем
    }
}

// ============ КОММЕНТАРИИ (ИСПРАВЛЕННАЯ ВЕРСИЯ) ============
let currentCommentWorkId = null;

function openComments(workId) {
    currentCommentWorkId = workId;
    document.getElementById('modal-comments').style.display = 'flex';
    document.getElementById('comments-list').innerHTML = '<p class="loader">Загрузка...</p>';

    if (API.isAuthed()) {
        document.getElementById('comment-form-container').style.display = 'block';
        document.getElementById('comment-login-hint').style.display = 'none';
    } else {
        document.getElementById('comment-form-container').style.display = 'none';
        document.getElementById('comment-login-hint').style.display = 'block';
    }

    loadComments(workId);
}

function closeComments() {
    document.getElementById('modal-comments').style.display = 'none';
    currentCommentWorkId = null;
}

async function loadComments(workId) {
    const list = document.getElementById('comments-list');
    try {
        const res = await fetch(`/api/comments/?work_id=${workId}`);
        const data = await res.json();
        if (!data.data || data.data.length === 0) {
            list.innerHTML = '<p style="text-align:center; color: var(--text-muted);">Пока нет комментариев</p>';
            return;
        }
        list.innerHTML = data.data.map(c => `
            <div style="border-bottom: 1px solid var(--border-color); padding: 10px 0;">
                <div style="font-weight: 600; font-size: 14px;">${esc(c.username)}</div>
                <div style="font-size: 13px; color: var(--text-muted); margin: 4px 0;">${esc(c.text)}</div>
                <div style="font-size: 11px; color: var(--text-muted);">${c.created_at}</div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = '<p style="color: #ef4444;">Ошибка загрузки</p>';
    }
}

async function submitComment() {
    const text = document.getElementById('comment-text').value.trim();
    const errBox = document.getElementById('comment-error');
    errBox.textContent = '';

    if (!text) {
        errBox.textContent = 'Введите текст комментария';
        return;
    }

    const token = API.token();
    if (!token) {
        errBox.textContent = 'Сессия истекла, войдите снова';
        return;
    }

    const body = new URLSearchParams();
    body.append('work_id', currentCommentWorkId);
    body.append('text', text);

    try {
        const res = await fetch('/api/comments/', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: body.toString()
        });
        const data = await res.json();

        if (res.ok && data.code === 201) {
            document.getElementById('comment-text').value = '';
            loadComments(currentCommentWorkId);
            toast('Комментарий добавлен', 'success');
        } else {
            errBox.textContent = data.message || 'Ошибка отправки';
        }
    } catch (e) {
        errBox.textContent = 'Ошибка сети';
        console.error(e);
    }
}