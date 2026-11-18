document.addEventListener('DOMContentLoaded', () => {
    fetchContests();
});

// Красивые картинки-заглушки (потому что в БД нет обложки конкурса)
const fallbackImages = [
    'https://images.unsplash.com/photo-1483347756197-71ef80e95f73?auto=format&fit=crop&w=500&q=80', // Сияние
    'https://images.unsplash.com/photo-1517404215738-15263e9f9178?auto=format&fit=crop&w=500&q=80', // Горы
    'https://images.unsplash.com/photo-1478719059408-592965723cbc?auto=format&fit=crop&w=500&q=80', // Зима
    'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=500&q=80', // Снег
    'https://images.unsplash.com/photo-1520763185298-1b434c919102?auto=format&fit=crop&w=500&q=80'  // Лес
];

async function fetchContests() {
    const grid = document.getElementById('contests-grid');
    const loader = document.getElementById('loader');
    const errorMsg = document.getElementById('error-message');

    loader.style.display = 'block';
    errorMsg.style.display = 'none';
    grid.innerHTML = '';

    try {
        const response = await fetch('/api/contests/', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

        const result = await response.json();
        loader.style.display = 'none';

        const contests = result.data || [];

        if (contests.length === 0) {
            grid.innerHTML = '<p style="color: #94a3b8;">Пока нет активных конкурсов. Загляните позже!</p>';
            return;
        }

        contests.forEach((contest, index) => {
            const card = document.createElement('div');
            card.className = 'card animate-card';
            // Задержка для эффекта каскадного появления
            card.style.animationDelay = `${index * 0.1}s`;

            const title = contest.title || 'Без названия';
            const description = contest.description || 'Описание пока не добавлено.';
            const status = (contest.status || 'draft').toLowerCase();
            const id = contest.id;

            // Выбираем картинку по кругу из массива
            const imageUrl = fallbackImages[index % fallbackImages.length];

            // Настраиваем цвет бейджа в зависимости от статуса
            let badgeClass = 'badge-draft';
            let statusText = 'Черновик';

            if (status === 'open') { badgeClass = 'badge-open'; statusText = 'Прием работ'; }
            else if (status === 'voting') { badgeClass = 'badge-voting'; statusText = 'Голосование'; }
            else if (status === 'closed') { badgeClass = 'badge-closed'; statusText = 'Завершен'; }

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${imageUrl}" alt="${title}" class="card-img" loading="lazy">
                    <span class="badge ${badgeClass}">${statusText}</span>
                </div>
                <div class="card-body">
                    <h3 class="card-title">${title}</h3>
                    <p class="card-text">${description}</p>
                    <a href="/contest/?id=${id}" class="btn card-btn">Подробнее</a>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (error) {
        console.error("Ошибка:", error);
        loader.style.display = 'none';
        errorMsg.style.display = 'block';
        errorMsg.textContent = "Не удалось загрузить конкурсы. Проверьте, запущен ли сервер.";
    }
}