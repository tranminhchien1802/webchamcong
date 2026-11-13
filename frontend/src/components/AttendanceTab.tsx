import { useCallback, useEffect, useState } from 'react'
import { getEmployees } from '../services/api'
import type { EmployeeAttendance } from '../types/face'
import { useCameraRecognition } from '../hooks/useCameraRecognition'
import { CameraView } from './CameraView'
import { EmployeeList } from './EmployeeList'

function formatAttendanceTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(value))
}

export function AttendanceTab() {
  const [action, setAction] = useState<'in' | 'out'>('in')
  const [employees, setEmployees] = useState<EmployeeAttendance[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)

  const refreshEmployees = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await getEmployees(signal)
      setEmployees(result)
      setListError(null)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setListError(error instanceof Error ? error.message : 'Could not load employees.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    // Loading from the API is the external synchronization owned by this effect.
    // oxlint-disable-next-line react/set-state-in-effect
    void refreshEmployees(controller.signal)
    const interval = window.setInterval(() => void refreshEmployees(), 5000)
    return () => {
      controller.abort()
      window.clearInterval(interval)
    }
  }, [refreshEmployees])

  const camera = useCameraRecognition({
    action,
    recognitionEnabled: employees.length > 0 && !listError,
    onAttendanceUpdated: refreshEmployees,
  })
  const recognizedEmployees = new Map<string, string>()
  for (const face of camera.faces) {
    if (face.employee_id) recognizedEmployees.set(face.employee_id, face.name)
  }
  const showAttendanceResults =
    camera.recognitionState !== 'backend-error' &&
    camera.recognitionState !== 'spoof-detected' &&
    recognizedEmployees.size > 0

  return (
    <section className="panel" aria-labelledby="attendance-title">
      <div className="panel-header">
        <div>
          <h2 id="attendance-title">Chấm công khuôn mặt</h2>
          <p>Chọn Vào ca hoặc Ra ca rồi nhìn vào camera. Giờ Việt Nam được ghi từ máy chủ.</p>
        </div>
        <span className="status-pill">Live session</span>
      </div>

      <div className="tabs" role="group" aria-label="Loại chấm công">
        <button type="button" className={action === 'in' ? 'tab active' : 'tab'} aria-pressed={action === 'in'} onClick={() => { if (action !== 'in') { camera.changeAction('in'); setAction('in') } }}>Vào ca</button>
        <button type="button" className={action === 'out' ? 'tab active' : 'tab'} aria-pressed={action === 'out'} onClick={() => { if (action !== 'out') { camera.changeAction('out'); setAction('out') } }}>Ra ca</button>
        <span>Đang chấm {action === 'out' ? 'giờ ra' : 'giờ vào'} — có thể đổi khi camera đang bật.</span>
      </div>
      <div className="camera-layout">
        <CameraView
          videoRef={camera.videoRef}
          cameraState={camera.cameraState}
          recognitionState={camera.recognitionState}
          faces={camera.faces}
          frameSize={camera.frameSize}
          error={camera.error}
          hasEmployees={employees.length > 0}
          onStart={camera.startCamera}
          onStop={camera.stopCamera}
        />
        <EmployeeList employees={employees} loading={loading} error={listError} />
      </div>

      {showAttendanceResults ? (
        <div className="attendance-confirmations" aria-live="polite">
          {[...recognizedEmployees].map(([employeeId, name]) => {
            const employee = employees.find((item) => item.employee_id === employeeId)
            const arrivedAt = action === 'out' ? employee?.departed_at : employee?.arrived_at

            return (
              <div className="attendance-confirmation" key={employeeId}>
                <span className="attendance-confirmation-check" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="m6.5 12.5 3.5 3.5 7.5-8" />
                  </svg>
                </span>
                <div className="attendance-confirmation-copy">
                  <strong>{name}</strong>
                  <span>
                    {arrivedAt
                      ? `${action === 'out' ? 'Đã ghi giờ ra' : 'Đã ghi giờ vào'}: ${formatAttendanceTime(arrivedAt)}`
                      : 'Recording attendance time…'}
                  </span>
                </div>
                <span className="attendance-confirmation-badge">
                  {arrivedAt ? 'Đã lưu' : 'Đang lưu'}
                </span>
              </div>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
