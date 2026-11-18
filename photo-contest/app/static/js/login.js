document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMsg = document.getElementById('error-message');
    const submitBtn = document.getElementById('submit-btn');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Останавливаем перезагрузку страницы

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        submitBtn.textContent = 'Загрузка...';
        submitBtn.disabled = true;
        errorMsg.style.display = 'none';

        try {
            // ВАЖНО: Отправляем данные как обычную форму, а не JSON!
            const formData = new URLSearchParams();
            formData.append('email', email);
            formData.append('password', password);

            const response = await fetch('/api/auth/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded' // Говорим, что это форма
                },
                body: formData.toString()
            });

            const data = await response.json();

            if (!response.ok) {
                // Если бэкенд вернул ошибку (401, 422 и т.д.), выводим её
                throw new Error(data.message || 'Неверный email или пароль');
            }

            // Твой бэкенд возвращает токен внутри объекта data: {"data": {"token": "..."}}
            const token = data.data?.token;

            if (token) {
                localStorage.setItem('auth_token', token); // Сохраняем токен

                // Если все ок, перекидываем на главную
                window.location.href = '/';
            } else {
                throw new Error('Сервер не вернул токен');
            }

        } catch (error) {
            console.error("Ошибка:", error);
            errorMsg.textContent = error.message;
            errorMsg.style.display = 'block';
            submitBtn.textContent = 'Войти';
            submitBtn.disabled = false;
        }
    });
});