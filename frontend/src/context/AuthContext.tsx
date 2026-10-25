"use client"
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type AuthContextType = {
  user: {
    id: string
    email: string
  } | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  authFetch: (url: string, options?: RequestInit) => Promise<Response>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Helper function to decode JWT token and extract user ID
const decodeToken = (token: string): { id: string } | null => {
  try {
    // JWT consists of three parts: header.payload.signature
    const payload = token.split('.')[1]
    if (!payload) return null

    // Replace URL-safe characters and decode
    const decoded = atob(
      payload.replace(/-/g, '+').replace(/_/g, '/')
    )

    const parsed = JSON.parse(decoded)
    return { id: parsed.sub || '' }
  } catch (error) {
    console.warn('Failed to decode token:', error)
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<{
    id: string
    email: string
  } | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      setToken(storedToken)
      // Verify token by getting current user (strict mode for app startup)
      fetchCurrentUser(true)
    } else {
      setIsLoading(false)
    }
  }, [])

  const fetchCurrentUser = async (strictMode = false) => {
    try {
      const response = await fetch(`${getApiBase()}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        // In strict mode (app startup), clear token on failure
        // In lenient mode (post-login/register), keep token but clear user state
        if (strictMode) {
          logout()
        } else {
          setUser(null)
        }
      }
    } catch (error) {
      // Network or parsing error
      if (strictMode) {
        logout()
      } else {
        setUser(null)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await fetch(`${getApiBase()}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error('Login failed')
    }

    const data = await response.json()
    setToken(data.access_token)
    localStorage.setItem('token', data.access_token)

    // Set optimistic user state from token
    const tokenUser = decodeToken(data.access_token)
    if (tokenUser) {
      setUser({
        id: tokenUser.id,
        email: email // Use the email from login attempt as placeholder
      })
    }

    setIsLoading(true)
    try {
      // Verify token and get real user data
      const response = await fetch(`${getApiBase()}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      })
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      }
      // If verification fails, we keep the optimistic user state
    } catch (error) {
      // If verification fails due to network/error, keep optimistic state
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, password: string) => {
    const response = await fetch(`${getApiBase()}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error('Registration failed')
    }

    const data = await response.json()
    setToken(data.access_token)
    localStorage.setItem('token', data.access_token)

    // Set optimistic user state from token
    const tokenUser = decodeToken(data.access_token)
    if (tokenUser) {
      setUser({
        id: tokenUser.id,
        email: email // Use the email from registration attempt as placeholder
      })
    }

    setIsLoading(true)
    try {
      // Verify token and get real user data
      const response = await fetch(`${getApiBase()}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      })
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      }
      // If verification fails, we keep the optimistic user state
    } catch (error) {
      // If verification fails due to network/error, keep optimistic state
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
  }

  const authFetch = async (url: string, options: RequestInit = {}) => {
    if (!token) {
      throw new Error('Not authenticated')
    }

    const headers = new Headers(options.headers)
    headers.set('Authorization', `Bearer ${token}`)

    return fetch(`${getApiBase()}${url}`, {
      ...options,
      headers,
    })
  }

  const getApiBase = () => {
    return process.env.NEXT_PUBLIC_RAG_API_URL || 'http://127.0.0.1:8000'
  }

  const value = {
    user,
    token,
    isLoading,
    login,
    register,
    logout,
    authFetch,
  }

  if (isLoading) {
    return <div>Loading...</div>
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}