# 📋 Task Manager

> Applicazione CLI open source per gestione task, scritta in Python.

---

## Stack Tecnologico

| Componente | Scelta        | Licenza      |
|------------|---------------|--------------|
| Linguaggio | Python 3.x    | PSF          |
| CLI        | click         | BSD-3-Clause |
| Logging    | loguru        | MIT          |
| Config     | pydantic      | MIT          |
| Storage    | JSON locale   | —            |

---

## Struttura Progetto

```
task_manager/
├── main.py              # Entry point
├── requirements.txt     # Dipendenze
├── tasks.json           # Storage locale (auto-generato)
├── task_manager.log     # Log file (auto-generato)
│
├── app/
│   ├── cli.py           # CLI Layer (Click)
│   └── service.py       # Application Layer (logica business)
│
├── domain/
│   └── models.py        # Domain Layer (modello Task)
│
└── utils/
    └── storage.py       # Utils Layer (config + persistenza JSON)
```

---

## Setup

```bash
# 1. Clona o scarica il progetto
cd task_manager

# 2. Crea virtual environment (consigliato)
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Avvia
python main.py --help
```

---

## Utilizzo

```bash
# Aggiungere un task
python main.py add "Studiare Python"
python main.py add "Scrivere tests"

# Elencare task attivi
python main.py list

# Elencare tutti i task (inclusi completati)
python main.py list --all

# Completare un task
python main.py done 1

# Eliminare un task
python main.py delete 2
```

---

## Architettura

```
[ CLI Layer ]        → app/cli.py
      ↓
[ Application Layer] → app/service.py
      ↓
[ Domain / Models ]  → domain/models.py
      ↓
[ Utils / Config ]   → utils/storage.py
```

---

## Evoluzioni Future

- [ ] API REST con **FastAPI**
- [ ] Database **SQLite**
- [ ] Containerizzazione con **Docker**
- [ ] Pipeline dati con **Apache Airflow**

---

## Licenza

MIT License — vedi `LICENSE`
