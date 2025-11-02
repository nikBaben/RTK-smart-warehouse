%% Keycloak взаимодействие
    KC -->|User Tokens| API
    FE -->|OAuth2 Flow / JWT| KC

    %% Docker
    subgraph DOCKER["🐳 Docker Compose / Containers"]
        Caddy
        FE
        API
        EMU
        SCH
        KC
        PG
        REDIS
    end

Компоненты проекта:
1. Backend — API на FastAPI   
2. Frontend — React + Redux Toolkit (RTK Query)  
3. AI Module — прогнозирование и аналитика  
4. Database — PostgreSQL  
5. Integration Layer — обработка RTK-данных от внешних устройств  

---

## ⚙️ Технологический стек

| Категория | Технологии |
|------------|-------------|
| 💻 Frontend | React, TypeScript, Vite, shadcn |
| ⚙️ Backend | FastAPI, SQLAlchemy |
| 🧠 Data & ML | Pandas, PyTorch |
| 🗄 Database | PostgreSQL, Redis, Keyclock |
| 🧰 DevOps | Docker, GitHub Actions, YandexCloud|

---

## 🧠 Команда проекта

| Участник | Роль | Контакты |
|-----------|------|-----------|
| Никита  | Backend Developer | [GitHub](https://github.com/nikBaben),[Telegram](@bab3n) |
| Матвей | Frontend Developer & UX/UI Designer | [GitHub](https://github.com/o2cloud) |
| Вадим | Frontend Developer | [GitHub](https://github.com/tailorsky) |
| Александр | Backend Developer | [GitHub](https://github.com/RikiTikiTavee17) |
| Захар | Backend Developer | [GitHub](https://github.com/ZaharPavlikov) |
| Евгений | Data Science Engineer | [GitHub](https://github.com/Mmm-max) |

---

>>>>>>> main
