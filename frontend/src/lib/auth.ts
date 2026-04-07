import { Amplify } from 'aws-amplify'
import { fetchAuthSession, signOut } from 'aws-amplify/auth'
import type { UserRole } from './models/types'

const USER_ROLES: string[] = ['it-admin', 'management', 'employee', 'finance']

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID?.trim()
const userPoolClientId =
  import.meta.env.VITE_COGNITO_APP_CLIENT_ID?.trim() ??
  import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID?.trim()
const identityPoolId = import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID?.trim()
const regionFromPoolId = userPoolId?.split('_')[0]
const region = import.meta.env.VITE_AWS_REGION?.trim() ?? regionFromPoolId

let isConfigured = false

export function getMissingAuthConfig(): string[] {
  const missing: string[] = []

  if (!userPoolId) {
    missing.push('VITE_COGNITO_USER_POOL_ID')
  }

  if (!userPoolClientId) {
    missing.push(
      'VITE_COGNITO_APP_CLIENT_ID or VITE_COGNITO_USER_POOL_CLIENT_ID',
    )
  }

  if (!region) {
    missing.push('VITE_AWS_REGION')
  }

  return missing
}

export function configureAmplifyAuth(): boolean {
  if (isConfigured) {
    return true
  }

  const missing = getMissingAuthConfig()

  if (missing.length > 0) {
    console.error(`Missing Cognito env vars: ${missing.join(', ')}`)
    return false
  }

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: userPoolId!,
        userPoolClientId: userPoolClientId!,
        ...(identityPoolId ? { identityPoolId } : {}),
        ...(region ? { loginWith: { email: true, username: true } } : {}),
      },
    },
  })

  isConfigured = true
  return true
}

export async function isAuthenticated(): Promise<boolean> {
  if (!configureAmplifyAuth()) {
    return false
  }

  try {
    const session = await fetchAuthSession()
    return session.tokens?.idToken != null
  } catch {
    return false
  }
}

export interface AuthSession {
  userId: string
  userRole: UserRole | null
  userAttributes: {
    email?: string
    name?: string
    given_name?: string
    family_name?: string
    [key: string]: string | undefined
  }
}

/**
 * Single Cognito call that extracts userId, role, and user attributes
 * from the ID token payload. Replaces the previous 3-call pattern
 * (getCurrentUser + fetchAuthSession + fetchUserAttributes).
 */
export async function getAuthSession(): Promise<AuthSession | null> {
  if (!configureAmplifyAuth()) {
    return null
  }

  try {
    const session = await fetchAuthSession()
    const payload = session.tokens?.idToken?.payload
    if (!payload) {
      return null
    }

    const customRole = payload['custom:role'] as string | undefined
    const userRole =
      customRole && USER_ROLES.includes(customRole)
        ? (customRole as UserRole)
        : null

    return {
      userId: payload.sub as string,
      userRole,
      userAttributes: {
        email: payload.email as string | undefined,
        name: payload.name as string | undefined,
        given_name: payload.given_name as string | undefined,
        family_name: payload.family_name as string | undefined,
      },
    }
  } catch {
    return null
  }
}

export function getRedirectTarget(target: string | undefined): string {
  if (!target || target.length === 0) {
    return '/'
  }

  if (!target.startsWith('/')) {
    return '/'
  }

  if (target.startsWith('//')) {
    return '/'
  }

  return target
}

import { wsManager } from './websocket'

export async function signOutCurrentUser() {
  wsManager.disconnect()
  await signOut()
}

configureAmplifyAuth()
