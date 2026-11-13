# Local attendance with Supabase

1. For a new project, run `schema.sql` in Supabase SQL Editor. For an existing
   installation, run `attendance_checkout.sql` to add the departure column and
   time-order constraint without deleting existing records.
2. Fill `SUPABASE_SECRET_KEY` in `backend/.env` with the project's server secret.
   Keep `STORAGE_BACKEND=supabase` and `FACE_ANTI_SPOOFING_ENABLED=true`.
3. Start the backend from the `backend` directory:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn --app-dir src backend.main:app --env-file .env --host 127.0.0.1 --port 8000
   ```

4. Open http://127.0.0.1:5173. Enroll the employee in this Supabase-backed
   instance, select Vào ca or Ra ca, then start the camera. Pause it to switch
   actions. Existing CSV employees are not automatically imported.

Each employee has one arrival and one departure per Vietnam calendar day.
Repeated frames preserve the original timestamps. Checkout requires an arrival
on that day; overnight shifts and multiple shifts per day are not supported.
Timestamps come from the backend clock; keep the server clock synchronized.

Matching requires a live-face check, one face in the frame, an encoding distance
at most FACE_RECOGNITION_TOLERANCE, and a minimum 0.05 distance advantage over
another employee. Failed liveness or storage checks do not report a saved punch.
The distance margin is a heuristic and must be evaluated with real camera data;
automated tests do not establish biometric accuracy or replay resistance.

Verify both timestamps in public.attendance after a real check-in and check-out.

Successful new punches also save a JPEG in the private Supabase Storage bucket
`attendance-photos` (created automatically by the backend). The path is
`YYYY-MM-DD/employee_id/in.jpg` or `YYYY-MM-DD/employee_id/out.jpg`, linking each
image to its daily attendance row. Repeated frames do not replace the image.
Existing punches from before this feature are not backfilled with new photos.
Uploads must succeed before the attendance row is written. If the database write
fails after upload, retrying preserves the first image and retries the row write.
Use Supabase Storage in the dashboard to inspect images; public access is disabled.

Browser camera permission is controlled by the browser. Use the same local URL
and choose persistent Allow in site settings to avoid repeated permission prompts.
