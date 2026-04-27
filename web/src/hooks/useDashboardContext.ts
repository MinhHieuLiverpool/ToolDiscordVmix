import { useOutletContext } from 'react-router-dom'
import type { DashboardContextType } from '../pages/DashboardLayout'

export function useDashboardContext() {
    return useOutletContext<DashboardContextType>()
}
