export interface EmployeeCreated {
  employee_id: string
  name: string
  image_filename: string
}

export interface EmployeeAttendance {
  employee_id: string
  name: string
  is_arrive: boolean
  arrived_at: string | null
  departed_at: string | null
}

export interface FaceLocation {
  top: number
  right: number
  bottom: number
  left: number
}

export interface RecognizedFace {
  employee_id: string | null
  name: string
  distance: number | null
  location: FaceLocation
}

export interface RecognitionResponse {
  faces: RecognizedFace[]
  attendance_updated: string[]
}

export type CameraState =
  | 'idle'
  | 'requesting'
  | 'active'
  | 'permission-denied'
  | 'unavailable'

export type RecognitionState =
  | 'idle'
  | 'recognizing'
  | 'recognized'
  | 'unknown'
  | 'no-face'
  | 'spoof-detected'
  | 'backend-error'
