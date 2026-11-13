import type {
  EmployeeAttendance,
  EmployeeCreated,
  RecognitionResponse,
} from '../types/face'

const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(
  /\/$/,
  '',
)

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, options)
  } catch {
    throw new ApiError(
      'Cannot reach the attendance server. Make sure the backend is running.',
      0,
    )
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the HTTP fallback message when the response is not JSON.
    }
    throw new ApiError(message, response.status)
  }

  return response.json() as Promise<T>
}

export async function enrollEmployee(
  name: string,
  image: File,
): Promise<EmployeeCreated> {
  const body = new FormData()
  body.append('name', name)
  body.append('image', image)
  return request<EmployeeCreated>('/api/employees', { method: 'POST', body })
}

export function getEmployees(signal?: AbortSignal): Promise<EmployeeAttendance[]> {
  return request<EmployeeAttendance[]>('/api/employees', { signal })
}

export async function recognizeFrame(
  image: Blob,
  signal?: AbortSignal,
  action: 'in' | 'out' = 'in',
): Promise<RecognitionResponse> {
  const body = new FormData()
  body.append('image', image, 'camera-frame.jpg')
  body.append('action', action)
  return request<RecognitionResponse>('/api/recognize', {
    method: 'POST',
    body,
    signal,
  })
}

export { ApiError }
