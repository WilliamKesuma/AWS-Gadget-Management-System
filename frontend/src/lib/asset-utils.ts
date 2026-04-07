import type { AssetStatus, UserRole } from './models/types'

export type HandoverState = 'pending' | 'completed' | 'available' | 'none'

export function getHandoverState(
  status: AssetStatus,
  assignmentDate: string | undefined,
): HandoverState {
  if (status === 'IN_STOCK' && assignmentDate) return 'pending'
  if (status === 'ASSIGNED' && assignmentDate) return 'completed'
  if (status === 'IN_STOCK' && !assignmentDate) return 'available'
  return 'none'
}

export type AssetAction =
  | 'assign'
  | 'view-handover-form'
  | 'view-signed-handover'
  | 'cancel-assignment'
  | 'accept-asset'

export function getVisibleActions(
  role: UserRole,
  status: AssetStatus,
  handoverState: HandoverState,
  isAssignedUser: boolean,
): AssetAction[] {
  if (role === 'management' || role === 'finance') return []

  if (role === 'it-admin') {
    if (status === 'IN_STOCK' && handoverState === 'available')
      return ['assign']
    if (status === 'IN_STOCK' && handoverState === 'pending')
      return ['view-handover-form', 'cancel-assignment']
    if (status === 'ASSIGNED' && handoverState === 'completed')
      return ['view-handover-form', 'view-signed-handover']
    return []
  }

  if (role === 'employee') {
    if (!isAssignedUser) return []
    if (status === 'IN_STOCK' && handoverState === 'pending')
      return ['view-handover-form', 'accept-asset']
    if (status === 'ASSIGNED' && handoverState === 'completed')
      return ['view-handover-form', 'view-signed-handover']
    return []
  }

  return []
}
