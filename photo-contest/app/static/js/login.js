/* ============================================================
   login.js — страница входа
   Зависимости: api.js
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // Если уже вошли — на главную
    if (API.isAuthed()) {
        window.location.href = '/';
        return;
    }

    const loginForm = document.getElementById('login-form');
    const errorMsg = document.getElementById('error-message');
    const submitBtn = document.getElementById('submit-btn');

    // Ссылка "Зарегистрироваться" открывает модалку из base.html
    document.getElementById('open-register')?.addEventListener('click', () => {
        openModal('modal-register');
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        submitBtn.textContent = 'Загрузка...';
        submitBtn.disabled = true;
        errorMsg.classList.remove('visible');

        const { ok, data } = await API.postForm('/api/auth/', { email, password });

        submitBtn.textContent = 'Войти';
        submitBtn.disabled = false;

        if (!ok) {
            errorMsg.textContent = data?.message || 'Неверный email или пароль';
            errorMsg.classList.add('visible');
            return;
        }

        const token = data?.data?.token;
        const refreshToken = data?.data?.refresh_token;
        const user = data?.data?.user;
        if (!token) {
            errorMsg.textContent = 'Сервер не вернул токен';
            errorMsg.classList.add('visible');
            return;
        }

        API.setSession(token, user || {});
        window.location.href = '/';
    });
});
