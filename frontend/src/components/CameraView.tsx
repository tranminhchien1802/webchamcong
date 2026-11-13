import type { RefObject } from 'react'
import type {
  CameraState,
  RecognitionState,
  RecognizedFace,
} from '../types/face'

interface CameraViewProps {
  videoRef: RefObject<HTMLVideoElement | null>
  cameraState: CameraState
  recognitionState: RecognitionState
  faces: RecognizedFace[]
  frameSize: { width: number; height: number }
  error: string | null
  hasEmployees: boolean
  onStart: () => void
  onStop: () => void
}

const cameraLabels: Record<CameraState, { title: string; detail: string }> = {
  idle: { title: 'Camera paused', detail: 'Start when you are ready' },
  requesting: { title: 'Requesting camera', detail: 'Waiting for browser permission' },
  active: { title: 'Camera active', detail: 'Scanning every second' },
  'permission-denied': { title: 'Chưa có quyền camera', detail: 'Chọn Luôn cho phép camera trong cài đặt trang web' },
  unavailable: { title: 'Camera unavailable', detail: 'Check your camera connection' },
}

function recognitionMessage(
  state: RecognitionState,
  faces: RecognizedFace[],
  hasEmployees: boolean,
  error: string | null,
) {
  if (!hasEmployees) return 'Enroll an employee before starting recognition.'
  if (state === 'recognizing') return 'Checking the current frame…'
  if (state === 'recognized') {
    const names = [...new Set(faces.filter((face) => face.employee_id).map((face) => face.name))]
    return `Recognized: ${names.join(', ')}`
  }
  if (state === 'unknown') return 'A face was found, but it did not match an employee.'
  if (state === 'no-face') return 'Camera is ready. Move a face into the frame.'
  if (state === 'spoof-detected') {
    return error ?? 'Photo or screen detected — use your live face. Attendance was not recorded.'
  }
  if (state === 'backend-error') return error ?? 'The recognition server is unavailable.'
  return 'Recognition will start automatically when the camera is active.'
}

export function CameraView({
  videoRef,
  cameraState,
  recognitionState,
  faces,
  frameSize,
  error,
  hasEmployees,
  onStart,
  onStop,
}: CameraViewProps) {
  const cameraLabel = cameraLabels[cameraState]
  const isError = ['permission-denied', 'unavailable'].includes(cameraState)

  return (
    <div className="camera-column">
      <div className="camera-toolbar">
        <div className="camera-status">
          <span
            className={`status-indicator${cameraState === 'active' ? ' active' : ''}${isError ? ' error' : ''}`}
          />
          <span>
            <strong>{cameraLabel.title}</strong>
            <span>{cameraLabel.detail}</span>
          </span>
        </div>
        {cameraState === 'active' ? (
          <button className="secondary-button" type="button" onClick={onStop}>
            Pause camera
          </button>
        ) : (
          <button
            className="secondary-button"
            type="button"
            disabled={cameraState === 'requesting'}
            onClick={() => void onStart()}
          >
            {cameraState === 'requesting' ? 'Starting…' : 'Start camera'}
          </button>
        )}
      </div>

      <div
        className={`camera-frame${recognitionState === 'spoof-detected' ? ' spoof-detected' : ''}`}
        style={{ aspectRatio: `${frameSize.width} / ${frameSize.height}` }}
      >
        <video ref={videoRef} muted playsInline aria-label="Live attendance camera" />
        {cameraState !== 'active' ? (
          <div className="camera-placeholder">
            <div>
              <span className="placeholder-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M4 7.5h11.5v9H4zM15.5 10l4.5-2.5v9L15.5 14" />
                </svg>
              </span>
              <strong>{cameraLabel.title}</strong>
              <p>{error ?? 'Your live camera preview will appear here.'}</p>
            </div>
          </div>
        ) : null}

        {cameraState === 'active' ? (
          <div className="detection-layer" aria-hidden="true">
            {faces.map((face, index) => {
              const top = (face.location.top / frameSize.height) * 100
              const left = (face.location.left / frameSize.width) * 100
              const width =
                ((face.location.right - face.location.left) / frameSize.width) * 100
              const height =
                ((face.location.bottom - face.location.top) / frameSize.height) * 100
              return (
                <div
                  className={`face-box${face.employee_id ? '' : ' unknown'}`}
                  key={`${face.location.left}-${face.location.top}-${index}`}
                  style={{ top: `${top}%`, left: `${left}%`, width: `${width}%`, height: `${height}%` }}
                >
                  <span className="face-label">
                    {face.name}
                    {face.distance === null ? '' : ` · ${face.distance.toFixed(2)}`}
                  </span>
                </div>
              )
            })}
          </div>
        ) : null}
        {cameraState === 'active' && recognitionState === 'spoof-detected' ? (
          <div className="spoof-warning" role="alert">
            <strong>Photo or phone screen detected</strong>
            <span>Use your live face. Attendance was not recorded.</span>
          </div>
        ) : null}
      </div>

      <div className="recognition-strip" role="status">
        {recognitionState === 'recognizing' ? <span className="spinner" /> : null}
        <strong>Recognition</strong>
        <span>{recognitionMessage(recognitionState, faces, hasEmployees, error)}</span>
      </div>
      <p>Để trình duyệt nhớ quyền camera, chọn “Luôn cho phép” cho địa chỉ web này.
        Ảnh được tự lưu riêng cho mỗi lần vào và ra thành công.</p>
    </div>
  )
}
