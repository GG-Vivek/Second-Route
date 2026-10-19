import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { HomePage } from '@/pages/HomePage'
import { HealthPage } from '@/pages/HealthPage'
import { UnitsListPage } from '@/pages/UnitsListPage'
import { UnitDetailPage } from '@/pages/UnitDetailPage'
import { NewIntakePage } from '@/pages/NewIntakePage'
import { NewInspectionPage } from '@/pages/NewInspectionPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="health" element={<HealthPage />} />
        <Route path="units" element={<UnitsListPage />} />
        <Route path="units/:id" element={<UnitDetailPage />} />
        <Route path="intake/new" element={<NewIntakePage />} />
        <Route path="units/:id/inspection/new" element={<NewInspectionPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}