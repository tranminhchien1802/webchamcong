import type { EmployeeAttendance } from '../types/face'

interface EmployeeListProps {
  employees: EmployeeAttendance[]
  loading: boolean
  error: string | null
}

function formatArrival(value: string | null): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(value))
}

export function EmployeeList({ employees, loading, error }: EmployeeListProps) {
  const arrivedCount = employees.filter((employee) => employee.is_arrive).length

  return (
    <aside className="employee-card" aria-labelledby="employees-heading">
      <div className="employee-card-header">
        <div>
          <h3 id="employees-heading">Today’s employees</h3>
          <p>{arrivedCount} arrived today</p>
        </div>
        <span className="count-badge" aria-label={`${employees.length} employees`}>
          {employees.length}
        </span>
      </div>

      {loading && employees.length === 0 ? (
        <div className="empty-list">Loading employees…</div>
      ) : null}
      {error ? <div className="list-error">{error}</div> : null}
      {!loading && !error && employees.length === 0 ? (
        <div className="empty-list">
          No employees enrolled yet. Use the enrollment tab to add someone.
        </div>
      ) : null}

      {employees.length > 0 ? (
        <ul className="employee-list">
          {employees.map((employee) => (
            <li className="employee-row" key={employee.employee_id}>
              <span className={`arrival-check${employee.is_arrive ? ' arrived' : ''}`}>
                {employee.is_arrive ? (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m6.5 12.5 3.5 3.5 7.5-8" />
                  </svg>
                ) : null}
              </span>
              <span>
                <span className="employee-name">{employee.name}</span>
                <span className="employee-id">{employee.employee_id}</span>
              </span>
              <span className={`arrival-time${employee.is_arrive ? ' arrived' : ''}`}>
                <span>Vào: {formatArrival(employee.arrived_at)}</span><br />
                <span>Ra: {formatArrival(employee.departed_at)}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </aside>
  )
}
