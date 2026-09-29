# RCMP — Railway Crowd Management & Stampede Risk Detection — Backend & AI Build Doc (V1)

> "RCMP" is a working title used throughout this doc so tables/routes/scripts have a consistent name to refer to. Rename it freely (find-and-replace) — it has zero effect on the architecture.

Reference document for building the FastAPI backend and AI inference pipeline end-to-end, stage by stage. Follow the stages in section 8 in order — each one assumes the previous is done. Table names, column names, and route paths in this document are final for V1; don't rename mid-build unless a stage tells you to. No application code is included anywhere in this doc on purpose — this is a spec and a checklist, not a tutorial; you write every line yourself as you go through each stage.

---

## 1. Project overview

RCMP is an AI-powered, web-based CCTV analytics pipeline designed to estimate platform edge crowd density and detect anomalous panic motions to provide early warnings for stampede risks at major Indian railway stations. Traditional computer vision systems rely on standard object detection (like YOLO), which fails in densely congested scenes due to severe occlusion, rendering bounding-box approaches ineffective for accurate crowd counting.

**Primary motives for building it:**
1. Get real, practical experience with advanced Computer Vision techniques (density estimation + spatio-temporal motion tracking) beyond standard object detection, utilizing PyTorch and OpenCV on a local GPU.
2. Build a predictive, real-world safety solution that synthesizes spatial density and temporal motion dynamics to calculate a "Stampede Risk Score."

**Who uses it:**
- **Viewers / Operators (public visitors)** — the audience. No login required. They upload CCTV footage for processing, view the dashboard to see processed video analytics, risk score graphs, and alert frames.

**Core processing flow:**
```
Upload short video (mp4) → FastAPI saves temporarily → OpenCV extracts frames → CSRNet (Density) + Farneback (Motion) → Risk Score calculated → High-risk frames saved to Cloudinary → Data logged to MySQL → Dashboard fetches JSON
```

---

## 2. Feature list (V1)

- **Video Upload:** Users can upload short video clips (e.g., 10-30 seconds) simulating CCTV feeds. The backend handles the file temporarily and deletes it after processing.
- **Advanced Crowd Counting:** Utilizes a Congested Scene Recognition Network (CSRNet) via PyTorch to generate high-fidelity crowd density heatmaps, allowing for accurate crowd enumeration even when individuals are heavily overlapping.
- **Panic Motion Detection:** Integrates dense optical flow analysis using the Farneback algorithm (OpenCV) to compute the velocity and directional vectors of the crowd's movement between frames.
- **Risk Score Engine:** A custom logic module that synthesizes spatial density and temporal motion dynamics to calculate a real-time "Stampede Risk Score" (0-100%).
- **Cloudinary Integration:** Automatically uploads processed frames where the "Risk Score" crosses a critical threshold, overlaying the density heatmap and motion trajectories. The raw video is never saved to the cloud, saving storage.
- **Analytics Dashboard API:** Serves structured JSON payloads containing the timeline of events (headcount, motion speed, risk score, timestamp, image URL) for the frontend to render graphs and tables.

**Deliberately excluded from V1** (matches scope): Live YouTube/CCTV stream processing, user authentication/login, multi-camera simultaneous tracking, and actual SMS/Email alerting (just logged in DB).

---

## 3. Architecture Rules

Since authentication is removed, the system acts as an open analytics engine:
- All endpoints (upload, view, list) are public.
- FastAPI `BackgroundTasks` is used heavily so the video upload API returns immediately to the user while the heavy PyTorch/OpenCV processing happens asynchronously.

---

## 4. Tech stack (locked)

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| AI Framework | PyTorch (CUDA enabled for RTX 3050) |
| CV Processing | OpenCV (cv2), NumPy |
| Media storage | Cloudinary (free tier) — stores high-risk alert frames only |
| Background Tasks | FastAPI native `BackgroundTasks` |

---

## 5. Folder structure

```
rcmp-backend/
├── main.py                          # FastAPI app instance, includes app_router, CORS setup
│
├── app/
│   ├── core/
│   │   └── config.py                # loads .env, exposes settings
│   │
│   ├── db/
│   │   ├── database.py             # engine
│   │   └── session.py              # SessionLocal, Base, get_db()
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py             # imports all models so Alembic can discover them
│   │   ├── video.py
│   │   └── analytics_event.py
│   │
│   ├── schemas/                    # Pydantic request/response models
│   │   ├── video_schema.py
│   │   └── analytics_schema.py
│   │
│   ├── controllers/                # route handlers
│   │   ├── video_controller.py     # handles uploads
│   │   └── analytics_controller.py # handles dashboard data fetching
│   │
│   ├── routes/                     # APIRouter definitions
│   │   ├── __init__.py             # app_router, includes all sub-routers
│   │   ├── video_route.py
│   │   └── analytics_route.py
│   │
│   ├── services/                   # business logic
│   │   ├── video_service.py        # handles temp file saving, background task triggering
│   │   ├── cloudinary_service.py   # handles image uploads
│   │   └── analytics_service.py    # queries for dashboard data
│   │
│   ├── ai/                         # THE CV BRAIN
│   │   ├── __init__.py
│   │   ├── csrnet_model.py          # PyTorch model definition & weight loading
│   │   ├── density_estimator.py     # Preps frame, runs CSRNet, returns headcount + heatmap
│   │   ├── motion_tracker.py        # Farneback optical flow logic
│   │   ├── risk_engine.py           # Combines density + motion -> Risk Score
│   │   └── pipeline.py             # The master loop: reads video, calls ai modules, saves DB/Cloudinary
│   │
├── weights/                        # Gitignored. Holds pre-trained CSRNet .pth files
├── temp_videos/                    # Gitignored. Holds uploaded videos temporarily
├── alembic/
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## 6. Database schema

Naming: tables plural snake_case, columns snake_case, every table gets `id INT PK AUTO_INCREMENT`.

### `videos`
Stores metadata about the uploaded video file itself.
| Column | Type | Notes |
|---|---|---|
| id | INT | PK |
| original_filename | VARCHAR(255) | NOT NULL |
| processed_status | ENUM('pending', 'processing', 'completed', 'failed') | DEFAULT 'pending' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### `analytics_events`
Stores the frame-by-frame timeline generated during processing. One video will have many events.
| Column | Type | Notes |
|---|---|---|
| id | INT | PK |
| video_id | INT | FK → videos.id, ON DELETE CASCADE |
| frame_number | INT | NOT NULL |
| timestamp_sec | FLOAT | Time in seconds from start of video |
| headcount | INT | Estimated people in frame |
| motion_speed | FLOAT | Average velocity magnitude of optical flow vectors |
| risk_score | INT | 0-100 calculated risk percentage |
| risk_level | ENUM('low', 'moderate', 'high', 'severe') | NOT NULL |
| alert_image_url | VARCHAR(500) | nullable — Cloudinary URL if risk_level is 'high' or 'severe' |

Add an index on `video_id` (every dashboard query filters by it).

---

## 7. Environment variables (`.env`)

```
DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

---

## 8. Build sequence

### Stage 0 — Project skeleton & CUDA PyTorch setup
a. Create and activate a virtual environment.
b. Install base dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `alembic`, `python-dotenv`, `pydantic-settings`, `python-multipart`, `cloudinary`.
c. **CRITICAL:** Install PyTorch with CUDA support (since you have an RTX 3050). Find the exact pip command on the official PyTorch website (usually looks like `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`).
d. Install OpenCV: `pip install opencv-python-headless numpy`.
e. Create the full folder structure from section 5, including `weights/` and `temp_videos/`. Add them to `.gitignore` immediately.
f. Write a bare `main.py`: FastAPI app instance, CORS setup, and one `GET /health` route returning `{"status": "ok"}`.
g. Run `uvicorn main:app --reload` and confirm it starts.

### Stage 1 — Config and DB connection
a. Write `core/config.py`: a `Settings` class that loads all variables from section 7 out of `.env`.
b. Write `db/database.py` and `db/session.py` exactly as standard FastAPI patterns dictate.
c. Confirm the DB connection works before writing models.

### Stage 2 — Models
a. Write `models/video.py` and `models/analytics_event.py` matching the schema in section 6 exactly.
b. Import them into `models/__init__.py` for Alembic.

### Stage 3 — Migrations
a. `alembic init alembic`. Point `env.py` to your `Base.metadata` and `settings.DATABASE_URL`.
b. Generate the first migration: `alembic revision --autogenerate -m "create initial tables"`.
c. Read the generated file, ensure ENUMs and Foreign Keys look correct.
d. `alembic upgrade head`. Verify tables exist in MySQL.

### Stage 4 — Cloudinary Service
a. Write `services/cloudinary_service.py`: initialize the Cloudinary client using settings. Write a helper function `upload_image(image_array_or_path)` that returns the secure URL.

### Stage 5 — AI Pipeline 1: CSRNet (Density Estimation)
*This is the hardest part. Take your time.*
a. Download a pre-trained CSRNet PyTorch model weight file (`.pth`) from a trusted GitHub repository (e.g., the original CSRNet-pytorch repo) and place it in your `weights/` folder.
b. Write `ai/csrnet_model.py`: Define the PyTorch neural network class exactly as the repository specifies (usually a modified VGG-16). Write a function to load the `.pth` weights into this model and set it to `model.eval()`.
c. Write `ai/density_estimator.py`:
   - Create a function `process_frame(frame, model)`.
   - Convert the OpenCV frame (NumPy array) to a PyTorch tensor, normalize it (mean/std), and unsqueeze it to add a batch dimension.
   - Run inference (`with torch.no_grad(): output = model(tensor)`).
   - The output is a density map. Sum the values of the output tensor (`torch.sum(output).item()`) to get the estimated headcount.
   - Return the headcount and the density map converted back to a NumPy array for visualization.
d. Test this locally on a single image of a crowd to ensure it returns a valid integer.

### Stage 6 — AI Pipeline 2: OpenCV Optical Flow (Motion Tracking)
a. Write `ai/motion_tracker.py`.
b. Write a function `calculate_optical_flow(prev_frame, curr_frame)`.
c. Convert both frames to grayscale.
d. Use `cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)`. This returns a 2-channel array (x and y flow vectors).
e. Calculate the magnitude of the vectors using `cv2.cartToPolar()` or NumPy math. Return the average magnitude (this represents the "motion speed" of the crowd).

### Stage 7 — Risk Engine & Master Pipeline
a. Write `ai/risk_engine.py`: 
   - Create a function `calculate_risk(headcount, motion_speed)`.
   - Implement a formula (e.g., `(headcount / max_expected_crowd) * 100 * motion_speed_multiplier`).
   - Clamp the result to the 0-100 range and round it to an integer before returning — the raw formula can exceed 100 or produce a float, and the DB column expects an INT between 0 and 100.
   - Return a score (0-100, clamped) and an ENUM string (`low`, `moderate`, `high`, `severe`).
b. Write `ai/pipeline.py`:
   - This function takes a video file path and a `video_id` (DB ID).
   - As the first step, update the `videos` row for this `video_id` to `processing`.
   - Wrap the frame-processing loop below in a try/except block.
   - Open video with `cv2.VideoCapture(video_path)`.
   - Read the first frame, then loop: read the next frame.
   - Call `density_estimator` and `motion_tracker`.
   - Call `risk_engine`.
   - If `risk_level` is `high` or `severe`: overlay the density heatmap on the frame using `cv2.applyColorMap()`, save the frame temporarily, call `cloudinary_service.upload_image()`, and get the URL.
   - Create a new `AnalyticsEvent` row in MySQL with the headcount, speed, risk score, and Cloudinary URL.
   - On successful completion of the loop: release the video capture, delete the local video file, and update the `videos` row to `completed`.
   - On any exception during the loop: catch it, log the error, release the video capture, update the `videos` row to `failed`, and leave the local video file in place (don't delete it) so it's available for debugging.

### Stage 8 — Video Upload API (No Auth)
a. Write `controllers/video_controller.py`:
   - Endpoint: `POST /videos/upload`.
   - Accepts `UploadFile`. Saves it to `temp_videos/`.
   - Creates a `Video` row in DB with status `pending`.
   - **CRITICAL:** Trigger `ai/pipeline.py` as a FastAPI `BackgroundTasks` task so the API returns immediately to the user while processing happens asynchronously.
b. Test upload via Swagger UI. Check your terminal logs to ensure the background task is processing frames and inserting rows into `analytics_events`.

### Stage 9 — Public Analytics API (Dashboard Data)
a. Write `schemas/analytics_schema.py` with lightweight Pydantic models.
b. Write `controllers/analytics_controller.py`:
   - `GET /videos` (list of all processed videos)
   - `GET /videos/{video_id}/events` (returns the full timeline of analytics events for graphing)
   - `GET /alerts/high-risk` (returns only events where risk_level is high/severe, for the alert table)
c. Wire up routes. Test that a user can fetch these endpoints.

### Stage 10 — Manual verification
a. Walk every route in `/docs`.
b. Upload a test video. Watch the backend logs process the frames.
c. Check MySQL to ensure rows are being created in `analytics_events`.
d. Check Cloudinary media library to ensure high-risk frames are being uploaded.
e. Verify the public endpoints return the correct JSON.

### Stage 11 — Deployment Prep
a. Freeze dependencies: `pip freeze > requirements.txt`.
b. Ensure `weights/`, `temp_videos/`, and `.env` are in `.gitignore`.
c. Push to GitHub.

---

### Stage 12 — Pipeline Optimisation & Risk Engine Recalibration (rev 2)

**Problem:**  After tuning the risk formula for testing, a 22-second video produced 200+ "high" and "severe" alerts with a matching Cloudinary upload for every one of them.  Two root causes were identified:
1. `MAX_EXPECTED_CROWD` was set to `80` (a test value), making even sparsely populated frames score dangerously high.
2. The pipeline processed every single frame, and uploaded a Cloudinary image for every frame whose risk level crossed the threshold — no batching, no cooldown.

**Changes made (both files under `app/ai/`):**

#### `risk_engine.py` — Threshold recalibration

| Constant / parameter | Old value | New value | Reason |
|---|---|---|---|
| `MAX_EXPECTED_CROWD` | `80` | `200` | Realistic upper bound for a busy station platform camera view. |
| Motion multiplier — very still (< threshold px/frame) | threshold=0.5, ×0.8 | threshold=1.0, ×0.8 | Wider still-crowd band; very small optical-flow values were wrongly classified as "walking". |
| Motion multiplier — walking (< threshold px/frame) | threshold=1.5, ×1.2 | threshold=3.0, ×1.1 | Threshold raised to accommodate normal pedestrian movement; multiplier eased from 1.2 → 1.1. |
| Motion multiplier — panic (≥ threshold px/frame) | ×1.8 | ×1.5 | 1.8× was too aggressive; amplified routine movement into "severe". |

Risk-level category boundaries (`low < 30`, `moderate < 60`, `high < 80`, `severe ≥ 80`) are **unchanged** — only the score itself is better-calibrated.

#### `pipeline.py` — Frame sampling only (rev 3, current)

One tuning constant controls the entire upload volume:

| Constant | Value | Effect |
|---|---|---|
| `FRAME_SAMPLE_INTERVAL` | `5` | Only 1 in every 5 frames is passed through CSRNet + optical flow. At 25 fps this gives ~5 analysis points/second — sufficient for crowd monitoring — while reducing inference work by **80 %**. Skipped frames still advance `prev_frame` so optical-flow accuracy on the next sampled pair is preserved. |

**Why `ALERT_COOLDOWN_SEC` was removed (rev 2 → rev 3):**

Rev 2 introduced a `ALERT_COOLDOWN_SEC = 3.0` cooldown that only allowed one Cloudinary upload per 3 seconds of video time. The problem: high/severe frames within the cooldown window were still recorded in `analytics_events` with `alert_image_url = NULL`. The dashboard rendered all high/severe events including those NULL-url rows, producing broken `<img>` icons. Removing the cooldown ensures every sampled high/severe frame always has a valid Cloudinary URL — no NULL `alert_image_url`, no broken images.

**Expected impact on a 22-second, 25-fps video (rev 3):**

| Metric | Before (rev 1) | Rev 2 | Rev 3 (current) |
|---|---|---|---|
| Frames analysed | ~550 | ~110 | ~110 |
| Max Cloudinary uploads | ~200+ | ≤ 7 (broken images) | = high/severe sampled frames |
| Broken dashboard images | Yes | Yes (NULL urls) | **None** |
| Processing time | Very slow | ~80% faster | ~80% faster |

**How to re-tune in the future:**
- Increase `MAX_EXPECTED_CROWD` if the venue has more than 200 people in a typical camera shot.
- Adjust `FRAME_SAMPLE_INTERVAL` (e.g., `10`) for longer/higher-fps videos to further reduce upload count.
- Do **not** re-introduce a cooldown without also updating the dashboard to handle NULL `alert_image_url` gracefully (e.g., show a placeholder card instead of a broken image).

---

## 9. API endpoint reference

All endpoints are public (JSON REST API). No session or cookies required.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Basic health check |
| POST | `/videos/upload` | Uploads a video file and triggers background CV processing |
| GET | `/videos` | List all processed videos and their overall status |
| GET | `/videos/{video_id}/events` | Timeline of analytics events (headcount, speed, risk over time) for dashboard graphs |
| GET | `/alerts/high-risk` | List of high-risk alert events including Cloudinary image URLs |

---

## 10. Frontend — prompts

You're building the frontend with an AI coding agent rather than by hand, so no step-by-step here — just the prompt, ready to paste in as-is. 

### 10.1 RCMP Dashboard — prompt

```
Build a permanent public-facing frontend dashboard for an AI-powered
Railway Crowd Management & Stampede Risk Detection system (RCMP) named AIRA. 
Users use this to upload CCTV video clips, view crowd density graphs, 
and review high-risk stampede alert images generated by a PyTorch/OpenCV 
backend.

STACK
React (functional components, hooks), React Router, plain CSS or CSS
modules. All data comes from a FastAPI backend at http://localhost:8000
(configurable via an environment variable, e.g. VITE_API_BASE_URL). 
No authentication is required.

DATA (read-only JSON endpoints)
- POST /videos/upload -> multipart/form-data upload, returns video metadata
- GET /videos -> list: id, original_filename, processed_status, created_at
- GET /videos/{video_id}/events -> list: timestamp_sec, headcount, 
  motion_speed, risk_score, risk_level
- GET /alerts/high-risk -> list: timestamp_sec, risk_level, 
  alert_image_url (Cloudinary URL to the overlaid heatmap image)

VISUAL STYLE — Professional Transit / Security Console
- Primary accent (buttons, active states): deep blue, around #0F172A
- Secondary accent (alerts, high risk): red/orange, around #EF4444
- Page background: dark slate, around #1E293B (this is a security console,
  dark mode is standard)
- Card/panel background: slate, around #334155, soft shadow, rounded 
  corners (8px)
- Text: light gray/white, around #F1F5F9
- Monospace font for technical numbers (headcount, speeds)

PAGES

1. Dashboard / Home
   - Top bar: "RCMP Security Console" title, "Upload Video" button
   - Grid of recent high-risk alert images (fetched from 
     /alerts/high-risk). Clicking an image opens a modal showing the 
     full image, timestamp, and risk score.
   - A side panel or section listing recently uploaded videos with their 
     processing status (pending, processing, completed).

2. Upload Video (Modal or dedicated page)
   - A drag-and-drop zone or file input for mp4/avi files.
   - When submitted, sends a POST multipart/form-data request to 
     /videos/upload.
   - Show a loading state, then a success toast saying "Video uploaded. 
     Processing started."

3. Analytics / Timeline View
   - Accessed by clicking a video from the Home page list.
   - Fetches /videos/{id}/events.
   - Top section: A line chart (use Chart.js or Recharts) showing 
     Headcount and Risk Score over time (timestamp_sec on X axis).
   - Bottom section: A table mapping the timeline: Time, Headcount, 
     Motion Speed, Risk Level (color-coded badges: Low=green, 
     Moderate=yellow, High=orange, Severe=red), Alert Image link 
     (if exists).

GENERAL UX
- Dark mode professional aesthetic.
- Loading states for every fetch (skeleton or spinner).
- Friendly empty states ("No videos uploaded yet").
- Responsive layout.

Organize code into components/, pages/, and api/ (fetch wrapper 
functions).
```