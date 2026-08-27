# GST Sahayak – AI-Powered GST Research Assistant (Part 1: Foundation Setup)

## 1. Project Purpose
**GST Sahayak** is designed as an AI-powered research assistant for Goods and Services Tax (GST) queries. 
Part 1 establishes a clean, modern foundation connecting a React + Vite JavaScript frontend with a Python FastAPI backend.

---

## 2. Folder Structure
```text
gst-sahayak/
├── backend/
│   ├── main.py              # FastAPI application & endpoints (/health, /api/test)
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React main component & backend connection logic
│   │   ├── App.css          # Application styles
│   │   ├── main.jsx         # React DOM entry point
│   │   └── index.css        # Global CSS reset & base styles
│   ├── index.html           # HTML template
│   ├── package.json         # Node package configuration
│   └── vite.config.js       # Vite configuration
├── .env.example             # Environment configuration template
├── .gitignore               # Git ignored patterns
└── README.md                # Documentation & instructions
```

---

## 3. How to Create a Python Virtual Environment

Open a terminal in the `gst-sahayak/backend` directory:

### Windows (PowerShell / CMD)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 4. How to Install Backend Dependencies

With your virtual environment activated:

```bash
pip install -r requirements.txt
```

---

## 5. How to Start FastAPI Server

Run Uvicorn inside the `backend/` directory:

```bash
uvicorn main:app --reload --port 8000
```

The server will start at `http://127.0.0.1:8000`. You can inspect the automatically generated docs at `http://127.0.0.1:8000/docs`.

---

## 6. How to Start React Development Server

Open a new terminal window in the `gst-sahayak/frontend` directory:

1. Install frontend dependencies:
   ```bash
   cmd /c npm install
   # or `npm install` if scripts are enabled
   ```

2. Start the Vite dev server:
   ```bash
   cmd /c npm run dev
   # or `npm run dev`
   ```

The application will be accessible at `http://localhost:5173`.

---

## 7. How to Test the Frontend-Backend Connection

1. Ensure the FastAPI backend server is running on `http://127.0.0.1:8000`.
2. Ensure the React frontend server is running on `http://localhost:5173`.
3. Open `http://localhost:5173` in your browser.
4. On load, the status badge will check `GET /health` and display **Backend Status: Connected**.
5. Click the **"Test Backend Connection"** button.
6. The app will fetch `GET /api/test` and display:
   > `Response: Frontend and backend communication successful`
