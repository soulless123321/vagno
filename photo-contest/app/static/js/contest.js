document.addEventListener('DOMContentLoaded', () => {
    // Получаем ID конкурса из адресной строки (например, contest.html?id=1)
    const urlParams = new URLSearchParams(window.location.search);
    const contestId = urlParams.get('id');

    if (!contestId) {
        alert("Конкурс не найден!");
        window.location.href = '/';
        return;
    }

    loadContestData(contestId);
    loadWorks(contestId);
    setupUploadForm(contestId);
});

// 1. Загрузка данных о самом конкурсе
async function loadContestData(id) {
    try {
        // Так как мы не знаем точный формат API для одного конкурса, запросим все и найдем нужный
        const response = await fetch('/api/contests/');
        const result = await response.json();
        const contests = result.data || [];

        const contest = contests.find(c => c.id == id);

        if (contest) {
            document.getElementById('contest-title').textContent = contest.title;
            document.getElementById('contest-desc').textContent = contest.description || 'Описание отсутствует';

            const statusBadge = document.getElementById('contest-status');
            const status = (contest.status || 'draft').toLowerCase();

            if (status === 'open') {
                statusBadge.textContent = 'Прием работ';
                statusBadge.className = 'badge badge-open';
                document.getElementById('upload-container').style.display = 'block'; // Показываем форму
            } else if (status === 'voting') {
                statusBadge.textContent = 'Голосование';
                statusBadge.className = 'badge badge-voting';
            } else {
                statusBadge.textContent = 'Завершен';
                statusBadge.className = 'badge badge-closed';
            }
        }
    } catch (error) {
        console.error("Ошибка загрузки конкурса:", error);
    }
}

// 2. Загрузка работ (галерея)
async function loadWorks(id) {
    const gallery = document.getElementById('works-gallery');
    const loader = document.getElementById('loader');
    const galleryTitle = document.getElementById('gallery-title');

    loader.style.display = 'block';
    gallery.innerHTML = '';

    try {
        // Предполагаем, что API поддерживает фильтрацию по contest_id
        const response = await fetch(`/api/works/?contest_id=${id}`);
        const result = await response.json();

        loader.style.display = 'none';
        galleryTitle.style.display = 'block';

        // Твой API может возвращать { data: [...] } или просто массив
        const works = result.data || result || [];

        if (works.length === 0) {
            gallery.innerHTML = '<p style="color: var(--text-muted);">Пока нет загруженных работ. Станьте первым!</p>';
            return;
        }

        works.forEach(work => {
            // Проверяем, одобрена ли работа (если есть поле status)
            if (work.status && work.status !== 'approved') return;

            const card = document.createElement('div');
            card.className = 'work-card';

            // Формируем путь к картинке. Если она лежит в media/
            const imageUrl = work.image.startsWith('http') ? work.image : `/media/${work.image}`;

            card.innerHTML = `
                <img src="${imageUrl}" alt="${work.title}" class="work-img" loading="lazy">
                <div class="work-info">
                    <h3 class="work-title">${work.title}</h3>
                    <p class="work-author">Автор: ${work.user_id || 'Неизвестен'}</p>
                    <div class="vote-count">Голосов: ${work.votes_count || 0}</div>
                </div>
            `;
            gallery.appendChild(card);
        });

    } catch (error) {
        console.error("Ошибка загрузки работ:", error);
        loader.style.display = 'none';
        gallery.innerHTML = '<p style="color: #ef4444;">Не удалось загрузить работы.</p>';
    }
}

// 3. Обработка формы загрузки
function setupUploadForm(contestId) {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadArea = document.querySelector('.upload-area');

    // Красивое отображение имени файла
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = `Выбран файл: ${fileInput.files[0].name}`;
            uploadArea.style.borderColor = 'var(--accent)';
        }
    });

    // Drag and Drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--accent)';
        uploadArea.style.background = 'rgba(56, 189, 248, 0.1)';
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--border-color)';
        uploadArea.style.background = 'transparent';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--border-color)';
        uploadArea.style.background = 'transparent';

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = `Выбран файл: ${fileInput.files[0].name}`;
        }
    });

    // Отправка формы
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const token = localStorage.getItem('auth_token');
        if (!token) {
            alert('Вы должны войти в систему, чтобы загрузить работу!');
            window.location.href = '/login/';
            return;
        }

        const title = document.getElementById('work-title').value;
        const file = fileInput.files[0];

        if (!file) {
            alert('Выберите файл!');
            return;
        }

        // Используем FormData для отправки файла
        const formData = new FormData();
        formData.append('title', title);
        formData.append('image', file); // Название поля должно совпадать с тем, что ждет бэкенд
        formData.append('contest_id', contestId);

        try {
            const response = await fetch('/api/works/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}` // Передаем токен!
                    // ВАЖНО: При отправке FormData ЗАГОЛОВОК Content-Type указывать НЕ НУЖНО,
                    // браузер сам установит его с правильным boundary.
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Ошибка при загрузке работы');
            }

            alert('Работа успешно загружена и отправлена на модерацию!');
            form.reset();
            fileNameDisplay.textContent = 'Нажмите, чтобы выбрать фото, или перетащите файл сюда';

            // Перезагружаем галерею
            loadWorks(contestId);

        } catch (error) {
            console.error("Ошибка:", error);
            alert(error.message);
        }
    });
}