# Face Recognition Attendance System

A local employee attendance application built with FastAPI, `face_recognition`,
OpenCV, React, and TypeScript. Employees are enrolled from a face photograph,
then the browser camera sends frames to the backend for recognition. Employee
encodings and daily attendance are stored in CSV files; no external database is
required.

## Features

- Enroll an employee from a JPG or PNG image containing exactly one face.
- Store the employee's 128-value face encoding in CSV format.
- Recognize employees from a live browser camera.
- Mark each employee as arrived once per day.
- Display live recognition results and today's employee attendance list.

## Project structure

```text
face_regconition/
├── backend/
│   ├── data/
│   │   ├── employees.csv
│   │   └── attendance.csv
│   ├── src/backend/
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   ├── package.json
│   └── bun.lock
└── docs/
```

## Prerequisites

Install the following software before running the project:

- [Python 3.12](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) for the frontend
- A modern browser with camera support
- A C/C++ compiler and CMake if `dlib` must be built locally

On macOS, the native build tools can be installed with:

```bash
xcode-select --install
brew install cmake
```

Install `uv` and Bun if they are not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
```

Restart the terminal after installation if the `uv` or `bun` commands are not
immediately available.

## 1. Download the project

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd face_regconition
```

If the project was downloaded as a ZIP file, extract it and open a terminal in
the extracted `face_regconition` directory instead.

## 2. Install backend dependencies

From the repository root:

```bash
uv python install 3.12
uv sync --project backend
```

This creates `backend/.venv` and installs FastAPI, Uvicorn, OpenCV,
`face_recognition`, and the remaining Python dependencies from
`backend/uv.lock`.

## 3. Install frontend dependencies

```bash
cd frontend
bun install
cd ..
```

## 4. Start the backend

Open the first terminal and run:

```bash
cd backend
uv run uvicorn --app-dir src backend.main:app --reload
```

The backend is available at:

- API: <http://127.0.0.1:8000>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Running the command from `backend/` ensures that the application uses:

```text
backend/data/employees.csv
backend/data/attendance.csv
```

Alternatively, run it from the repository root with an explicit data path:

```bash
FACE_DATA_DIR=backend/data uv run --project backend \
  uvicorn --app-dir backend/src backend.main:app --reload
```

## 5. Start the frontend

Keep the backend running. Open a second terminal from the repository root and
run:

```bash
cd frontend
bun run dev
```

Open <http://localhost:5173> in the browser and allow camera access when asked.
Camera access normally requires either `localhost` or an HTTPS connection.

## Using the application

### Enroll an employee

1. Open the **Employee enrollment** tab.
2. Enter the employee's name.
3. Select a JPG, JPEG, or PNG image.
4. Use a clear image containing exactly one visible face.
5. Submit the form.

The backend detects the face, creates its encoding, and adds the employee to
`backend/data/employees.csv`.

### Record attendance

1. Open the **Attendance camera** tab.
2. Allow browser camera permission.
3. Position the employee's face clearly inside the camera view.
4. Wait for the recognition result.

After a successful match, the employee is marked as arrived and a row is added
to `backend/data/attendance.csv`. An employee receives only one attendance row
per day, even when recognized multiple times.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/employees` | Enroll an employee from a name and image |
| `GET` | `/api/employees` | List employees with today's attendance |
| `POST` | `/api/recognize` | Recognize faces in a camera frame |
| `GET` | `/api/attendance` | List attendance, optionally by date |

## Configuration

The defaults work for local development. Backend settings can be changed with
environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `FACE_DATA_DIR` | `data` | Directory containing the CSV files |
| `FACE_RECOGNITION_TOLERANCE` | `0.45` | Conservative maximum distance accepted as a match |
| `FACE_RECOGNITION_FRAME_SCALE` | `0.5` | Scale applied before live recognition |
| `FACE_DETECTION_MODEL` | `hog` | Face detector: `hog` or `cnn` |
| `FACE_ANTI_SPOOFING_ENABLED` | `true` | Run DeepFace's anti-spoofing check before identity recognition |

Live recognition checks each camera frame with DeepFace anti-spoofing before
matching the existing employee encoding. A spoof is rejected with HTTP 403; if
the anti-spoof model cannot load, recognition fails closed with HTTP 503. The
first check downloads DeepFace's model weights, so the Render service needs
outbound access and enough runtime memory for PyTorch and the model.

## Store data in Supabase

The backend supports Supabase PostgreSQL. To set up a new Supabase project:

1. Create a project in Supabase.
2. In the project's **SQL Editor**, run [`backend/supabase/schema.sql`](backend/supabase/schema.sql).
   This creates the `employees` and `attendance` tables, employee ID sequence,
   uniqueness constraints, and service-role-only access.
3. Set the following variables in the backend's PowerShell session, replacing
   the placeholders with values from your Supabase project:

   ```powershell
   $env:STORAGE_BACKEND = "supabase"
   $env:SUPABASE_URL = "https://<project-ref>.supabase.co"
   $env:SUPABASE_SECRET_KEY = "<server-only-secret-key>"
   ```

4. Start the backend from `backend/` as usual. Keep `SUPABASE_SECRET_KEY` on
   the backend only; never put it in frontend variables or commit it to Git.

The app will write new enrollments and attendance to Supabase when started with
`STORAGE_BACKEND=supabase`. To import existing CSV records, first run the
migration script without `--apply` to validate them, then add `--apply` to
import after reviewing the dry-run result:

```powershell
uv run python scripts/migrate_csv_to_supabase.py
uv run python scripts/migrate_csv_to_supabase.py --apply
```

The apply command requires `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the
environment. See [`docs/supabase_implement_spec.md`](docs/supabase_implement_spec.md)
for the complete setup and migration notes.

## Deploying the backend to Render

Set the Render service's root directory to `backend`. Use this build command so
Render installs the prebuilt `dlib-bin` wheel and skips compiling the `dlib`
source distribution (the two distributions provide the same `dlib` Python
module):

```bash
uv lock && uv sync --frozen --no-dev --no-install-package dlib
```

Use this start command:

```bash
uv run --no-sync uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port $PORT
```

Keep `dlib-bin` in `backend/pyproject.toml`; the lock command updates
`backend/uv.lock` during the Render build. Do not remove
`--no-install-package dlib` from the sync command, or Render will try to
compile `dlib` from source again.
| `FACE_ENCODING_MODEL` | `small` | Face landmarks model: `small` or `large` |
| `FACE_DETECTION_UPSAMPLE` | `1` | Detection upsample count |
| `FACE_ENCODING_JITTERS` | `1` | Face encoding sample count |
| `FACE_MAX_UPLOAD_BYTES` | `5242880` | Maximum uploaded image size |
| `FACE_TIMEZONE` | `Asia/Ho_Chi_Minh` | Attendance timezone |
| `FACE_LOG_LEVEL` | `INFO` | Backend logging level |
| `FACE_CORS_ORIGINS` | local ports | Comma-separated allowed frontend origins |

To display detailed backend logs:

```bash
cd backend
FACE_LOG_LEVEL=DEBUG uv run uvicorn --app-dir src backend.main:app --reload
```

The frontend uses `http://127.0.0.1:8000` by default. To use another backend,
create `frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Restart the frontend after changing this file.

## Run checks

Backend tests:

```bash
cd backend
PYTHONPATH=src uv run python -m unittest discover -s tests -q
```

Frontend lint and production build:

```bash
cd frontend
bun run lint
bun run build
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'backend'`

The backend uses a `src/` package layout. Include the application directory in
the Uvicorn command:

```bash
cd backend
uv run uvicorn --app-dir src backend.main:app --reload
```

### The camera is visible but no recognition request appears

Open the browser developer console and look for messages beginning with
`[recognition]`. The backend terminal should receive requests like:

```text
POST /api/recognize HTTP/1.1 200 OK
```

If the backend shows only `GET /api/employees`, hard-refresh the frontend and
confirm that the browser has camera permission.

### A face is detected but not matched

Check the backend logs for `Face not matched` and its nearest distance. Enroll
the employee with a clear, front-facing image under good lighting. Avoid
loosening the recognition tolerance unless the false-match tradeoff is
understood.

### `pkg_resources is deprecated` warning

This warning comes from the current `face_recognition_models` package. It does
not prevent the server or recognition pipeline from running.

## Privacy and limitations

- Face encodings and attendance records remain in local CSV files.
- This prototype does not implement liveness detection; a photograph may be
  accepted as a real face.
- CSV storage is intended for a local prototype and is not suitable for a
  high-concurrency production deployment.
