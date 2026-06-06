# 🖥️ MyServer — Linux Web Shell

Полноценный веб-терминал Ubuntu прямо в браузере, запускаемый через GitHub Actions.

## 🚀 Как запустить

### 1. Получи Ngrok токен
1. Зайди на [dashboard.ngrok.com](https://dashboard.ngrok.com)
2. Зарегистрируйся (бесплатно)
3. Скопируй **Auth Token** в разделе `Your Authtoken`

### 2. Запусти GitHub Action
1. Зайди в репозиторий → вкладка **Actions**
2. Выбери **🖥️ MyServer — Linux Web Shell**
3. Нажми **Run workflow**
4. Вставь свой Ngrok токен
5. Нажми **Run workflow** (зелёная кнопка)

### 3. Получи ссылку
- Подожди ~15 секунд
- В логах Action появится ссылка вида `https://xxxx.ngrok-free.app`
- Открой её в браузере — и ты в Ubuntu!

## ✨ Возможности
- 🐚 Полноценный bash shell (Ubuntu Latest)
- 📁 Загрузка файлов через браузер
- 🎨 Красивый терминал с подсветкой (xterm.js)
- 🔄 Автопереподключение
- 🛠️ Предустановлены: `curl`, `wget`, `git`, `vim`, `nano`, `python3`, `nodejs`, `npm`, `ffmpeg`, и многое другое
- ⏱️ Работает до 6 часов (лимит GitHub Actions)

## ⚠️ Важно
- Сессия работает **до 6 часов** (бесплатный лимит GitHub Actions)
- Каждый раз при запуске — **чистая Ubuntu** (данные не сохраняются между сессиями)
- Ngrok бесплатный план: 1 туннель одновременно
