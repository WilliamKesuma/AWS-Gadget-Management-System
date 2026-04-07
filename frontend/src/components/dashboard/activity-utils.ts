import {
  Monitor,
  UserPlus,
  AlertTriangle,
  RefreshCw,
  AppWindow,
  Trash2,
  CheckCircle,
  FileCheck,
  type LucideIcon,
} from 'lucide-react'
import type { ActivityType } from '#/lib/models/types'

type IconConfig = { icon: LucideIcon; bg: string; color: string }

export const ACTIVITY_ICON_MAP: Record<ActivityType, IconConfig> = {
  ASSET_CREATION: { icon: Monitor, bg: 'bg-info-subtle', color: 'text-info' },
  ASSIGNMENT: {
    icon: UserPlus,
    bg: 'bg-info-subtle',
    color: 'text-info',
  },
  RETURN: { icon: RefreshCw, bg: 'bg-warning-subtle', color: 'text-warning' },
  ISSUE: { icon: AlertTriangle, bg: 'bg-danger-subtle', color: 'text-danger' },
  SOFTWARE_REQUEST: {
    icon: AppWindow,
    bg: 'bg-info-subtle',
    color: 'text-info',
  },
  DISPOSAL: { icon: Trash2, bg: 'bg-muted', color: 'text-muted-foreground' },
  USER_CREATION: {
    icon: UserPlus,
    bg: 'bg-info-subtle',
    color: 'text-info',
  },
  APPROVAL: { icon: CheckCircle, bg: 'bg-info-subtle', color: 'text-info' },
  HANDOVER: { icon: FileCheck, bg: 'bg-info-subtle', color: 'text-info' },
}

export const ACTIVITY_BADGE_VARIANT: Record<
  ActivityType,
  'info' | 'warning' | 'danger' | 'secondary'
> = {
  ASSET_CREATION: 'info',
  ASSIGNMENT: 'info',
  RETURN: 'warning',
  ISSUE: 'danger',
  SOFTWARE_REQUEST: 'info',
  DISPOSAL: 'danger',
  USER_CREATION: 'secondary',
  APPROVAL: 'info',
  HANDOVER: 'info',
}
