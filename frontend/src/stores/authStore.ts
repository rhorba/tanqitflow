import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  userId: string | null
  role: string | null
  tenantSlug: string | null
  setAuth: (token: string) => void
  clearAuth: () => void
}

function parseJwt(token: string): Record<string, unknown> {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return {}
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      userId: null,
      role: null,
      tenantSlug: null,

      setAuth(token) {
        const payload = parseJwt(token)
        set({
          accessToken: token,
          userId: payload.sub as string,
          role: payload.role as string,
          tenantSlug: payload.tenant_slug as string,
        })
      },

      clearAuth() {
        set({ accessToken: null, userId: null, role: null, tenantSlug: null })
      },
    }),
    { name: 'tanqitflow-auth' }
  )
)
