import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import { Monitor, LogOut, Moon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Avatar, AvatarFallback } from '../ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu'
import { Switch } from '../ui/switch'
import { signOutCurrentUser } from '#/lib/auth'
import {
  useCurrentUserRole,
  useCurrentUserAttributes,
} from '#/hooks/use-current-user'
import type { FileRouteTypes } from '#/routeTree.gen'
import type { UserRole } from '#/lib/models/types'
import { Badge } from '../ui/badge'
import { NotificationsPanel } from './NotificationsPanel'
import { UserRoleLabels } from '#/lib/models/labels'

type NavItem = {
  label: string
  to: FileRouteTypes['to']
}

const NAV_ITEMS_BY_ROLE: Record<UserRole, NavItem[]> = {
  'it-admin': [
    { label: 'Dashboard', to: '/' },
    { label: 'Assets', to: '/assets' },
    { label: 'Users', to: '/users' },
    { label: 'Requests', to: '/requests' },
  ],
  management: [
    { label: 'Dashboard', to: '/' },
    { label: 'Approvals', to: '/approvals' },
    { label: 'Assets', to: '/assets' },
  ],
  finance: [
    { label: 'Dashboard', to: '/' },
  ],
  employee: [
    { label: 'Dashboard', to: '/' },
    { label: 'My Assets', to: '/assets' },
    { label: 'My Requests', to: '/requests' },
    { label: 'Pending Signatures', to: '/pending-signatures' },
  ],
}

export function Header() {
  const router = useRouterState()
  const navigate = useNavigate()
  const role = useCurrentUserRole()
  const userAttributes = useCurrentUserAttributes()
  const { theme, setTheme } = useTheme()

  const navItems: NavItem[] = role ? (NAV_ITEMS_BY_ROLE[role] ?? []) : []

  const displayName = userAttributes?.name ?? userAttributes?.given_name ?? ''
  const email = userAttributes?.email ?? ''
  const fallback = (displayName || email).charAt(0).toUpperCase() || '?'

  async function handleSignOut() {
    await signOutCurrentUser()
    await navigate({ to: '/login' })
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-card">
      <div className="flex h-16 items-center px-6">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2">
            <Monitor className="h-6 w-6 text-primary" strokeWidth={2.5} />
            <h1 className="text-lg font-bold text-foreground">
              {role ? UserRoleLabels[role] : 'Gadget Admin'}
            </h1>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            {navItems.map((item) => {
              const isActive =
                router.location.pathname === item.to ||
                (item.to !== '/' &&
                  router.location.pathname.startsWith(item.to))
              return (
                <Link
                  key={item.label}
                  to={item.to}
                  className={`transition-colors hover:text-foreground/80 ${isActive ? 'text-primary font-semibold' : 'text-muted-foreground font-semibold'}`}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="ml-auto flex items-center space-x-1 sm:space-x-2">
          <NotificationsPanel />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                aria-label="User menu"
                className="ml-2 rounded-full ring-offset-background transition-all hover:ring-2 hover:ring-ring hover:ring-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <Avatar className="h-8 w-8 cursor-pointer">
                  <AvatarFallback>{fallback}</AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-72 max-w-72">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col gap-1">
                  <div className="flex gap-2 place-items-center">
                    <Avatar>
                      <AvatarFallback>{fallback}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium leading-none text-wrap">
                        {displayName}
                      </p>
                      <p className="text-sm text-muted-foreground leading-none text-wrap mt-0.5">
                        {email}
                      </p>
                      {role && (
                        <Badge className="mt-1.5">{UserRoleLabels[role]}</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={(e) => e.preventDefault()}
                className="justify-between"
              >
                <span className="flex items-center gap-2">
                  <Moon className="h-4 w-4" />
                  Dark mode
                </span>
                <Switch
                  size="sm"
                  aria-label="Toggle dark mode"
                  checked={theme === 'dark'}
                  onCheckedChange={(checked) =>
                    setTheme(checked ? 'dark' : 'light')
                  }
                />
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleSignOut} variant="destructive">
                <LogOut className="h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
