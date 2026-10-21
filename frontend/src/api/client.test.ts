import { describe, it, expect, beforeEach } from 'vitest'
import { getOrgId, setOrgId } from '@/api/client'

describe('the organisation', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('is remembered once it has been set', () => {
    setOrgId('org-1')
    expect(getOrgId()).toBe('org-1')
  })

  it('is forgotten when it is cleared', () => {
    setOrgId('org-1')
    setOrgId(null)
    expect(getOrgId()).not.toBe('org-1')
  })

  it('survives a browser that will not store it', () => {
    const getItem = window.localStorage.getItem
    const setItem = window.localStorage.setItem
    window.localStorage.getItem = () => {
      throw new Error('storage is disabled')
    }
    window.localStorage.setItem = () => {
      throw new Error('storage is disabled')
    }

    try {
      expect(() => setOrgId('org-1')).not.toThrow()
      expect(() => getOrgId()).not.toThrow()
    } finally {
      window.localStorage.getItem = getItem
      window.localStorage.setItem = setItem
    }
  })
})
