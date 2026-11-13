import { useState } from 'react'
import { AttendanceTab } from './components/AttendanceTab'
import { EnrollmentTab } from './components/EnrollmentTab'
import './App.css'

type ActiveTab = 'enrollment' | 'attendance'

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('attendance')

  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="#top" aria-label="Attendly home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M8.5 4.75a3.25 3.25 0 1 0 0 6.5 3.25 3.25 0 0 0 0-6.5ZM3.75 19v-1.5A3.75 3.75 0 0 1 7.5 13.75h2A3.75 3.75 0 0 1 13.25 17.5V19M16.25 7.25h4m-2-2v4m-2 5.5h4m-2-2v4" />
            </svg>
          </span>
          <span>Attendly</span>
        </a>
        <div className="header-meta">
          <span className="live-dot" />
          Chấm công khuôn mặt
        </div>
      </header>

      <main id="top" className="main-content">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">Face recognition attendance</p>
          <h1 id="page-title">A faster way to welcome your team.</h1>
          <p className="intro-copy">
            Enroll employees once, then let the attendance camera recognize them
            as they arrive.
          </p>
        </section>

        <nav className="tabs" aria-label="Attendance workflows">
          <button
            className={activeTab === 'enrollment' ? 'tab active' : 'tab'}
            type="button"
            aria-selected={activeTab === 'enrollment'}
            onClick={() => setActiveTab('enrollment')}
          >
            <span className="tab-number">01</span>
            Employee enrollment
          </button>
          <button
            className={activeTab === 'attendance' ? 'tab active' : 'tab'}
            type="button"
            aria-selected={activeTab === 'attendance'}
            onClick={() => setActiveTab('attendance')}
          >
            <span className="tab-number">02</span>
            Attendance camera
          </button>
        </nav>

        <div className="workspace">
          {activeTab === 'enrollment' ? (
            <EnrollmentTab onEnrolled={() => setActiveTab('attendance')} />
          ) : (
            <AttendanceTab />
          )}
        </div>
      </main>

      <footer>
        <span>Dữ liệu được lưu qua máy chủ chấm công.</span>
        <span>Xác minh khuôn mặt thật trước khi ghi công.</span>
      </footer>
    </div>
  )
}

export default App
