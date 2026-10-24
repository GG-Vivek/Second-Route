import { describe, it, expect } from 'vitest'
import {
  retailerPayload,
  retailerSignUpSchema,
  signInSchema,
  userPayload,
  userSignUpSchema,
} from '@/auth/schemas'

const retailer = {
  organisationName: 'Harbour Electronics',
  displayName: 'Ada Okafor',
  email: 'ada@harbour.example',
  password: 'correct horse 42',
  riskProfile: 'balanced' as const,
}

describe('the retailer sign-up rules', () => {
  it('accepts a complete retailer', () => {
    expect(retailerSignUpSchema.safeParse(retailer).success).toBe(true)
  })

  it('asks for a letter and a number in the password, and says which is missing', () => {
    const noNumber = retailerSignUpSchema.safeParse({ ...retailer, password: 'onlyletters' })
    expect(noNumber.success).toBe(false)
    if (!noNumber.success) {
      expect(noNumber.error.issues.map((issue) => issue.message)).toContain('Use at least one number.')
    }
  })

  it('asks for a password of at least ten characters', () => {
    const short = retailerSignUpSchema.safeParse({ ...retailer, password: 'a1' })
    expect(short.success).toBe(false)
  })

  it('refuses an address that is not an address', () => {
    expect(retailerSignUpSchema.safeParse({ ...retailer, email: 'not-an-email' }).success).toBe(false)
  })

  it('sends the backend its own field names', () => {
    expect(retailerPayload(retailer)).toEqual({
      organisation_name: 'Harbour Electronics',
      display_name: 'Ada Okafor',
      email: 'ada@harbour.example',
      password: 'correct horse 42',
      risk_profile: 'balanced',
    })
  })
})

describe('the staff sign-up rules', () => {
  const staff = {
    inviteCode: '29b1eb4b-d353-4193-b173-538175757067',
    displayName: 'Kwame',
    email: 'kwame@harbour.example',
    password: 'another pass 7',
  }

  it('accepts a retailer code that is an identifier', () => {
    expect(userSignUpSchema.safeParse(staff).success).toBe(true)
  })

  it('says what a retailer code looks like when it is wrong', () => {
    const result = userSignUpSchema.safeParse({ ...staff, inviteCode: 'harbour' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toMatch(/retailer code/)
    }
  })

  it('sends the code under the name the backend uses', () => {
    expect(userPayload(staff)).toMatchObject({ invite_code: staff.inviteCode, display_name: 'Kwame' })
  })
})

describe('the sign-in rules', () => {
  it('asks for an email and a password, and nothing more', () => {
    expect(signInSchema.safeParse({ email: 'ada@harbour.example', password: 'x' }).success).toBe(true)
    expect(signInSchema.safeParse({ email: '', password: '' }).success).toBe(false)
  })
})
