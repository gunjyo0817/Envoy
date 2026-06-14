import { Outlet } from 'react-router-dom'
import BottomNav from '../components/BottomNav'

export default function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-[var(--color-bg)]">
      <div className="flex-1">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  )
}
