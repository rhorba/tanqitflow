import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  userId: string | null
  role: string | null
  tenantSlug: string | null
  languagePref: 'fr' | 'ar'
  setAuth: (token: string) => void
  setLanguagePref: (lang: 'fr' | 'ar') => void
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
      languagePref: 'fr',

      setAuth(token) {
        const payload = parseJwt(token)
        set({
          accessToken: token,
          userId: payload.sub as string,
          role: payload.role as string,
          tenantSlug: payload.tenant_slug as string,
        })
      },

      setLanguagePref(lang) {
        set({ languagePref: lang })
      },

      clearAuth() {
        set({ accessToken: null, userId: null, role: null, tenantSlug: null })
      },
    }),
    { name: 'tanqitflow-auth' }
  )
)
