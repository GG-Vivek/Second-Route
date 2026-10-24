import { z } from 'zod'

/**
 * The rules a sign-up has to meet (F11.1).
 *
 * They mirror the backend's rules, so a person hears about a mistake before the
 * request is sent, and the backend remains the one that decides. The messages
 * are the ones a person reads, so each one says what to change.
 */

export const PASSWORD_MIN_LENGTH = 10
export const PASSWORD_MAX_LENGTH = 128

const emailField = z
  .string()
  .trim()
  .min(1, 'Enter your email address.')
  .email('That does not look like an email address.')

const passwordField = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Use at least ${PASSWORD_MIN_LENGTH} characters.`)
  .max(PASSWORD_MAX_LENGTH, 'That password is too long.')
  .refine((value) => /[A-Za-z]/.test(value), 'Use at least one letter.')
  .refine((value) => /\d/.test(value), 'Use at least one number.')

const nameField = z.string().trim().min(1, 'Enter your name.').max(120, 'That name is too long.')

export const retailerSignUpSchema = z.object({
  organisationName: z
    .string()
    .trim()
    .min(2, 'Enter the name of your business.')
    .max(200, 'That name is too long.'),
  displayName: nameField,
  email: emailField,
  password: passwordField,
  riskProfile: z.enum(['conservative', 'balanced', 'aggressive']),
})

export const userSignUpSchema = z.object({
  inviteCode: z
    .string()
    .trim()
    .uuid('A retailer code is a long string with dashes in it. Check the code you were given.'),
  displayName: nameField,
  email: emailField,
  password: passwordField,
})

export const signInSchema = z.object({
  email: emailField,
  password: z.string().min(1, 'Enter your password.'),
})

export type RetailerSignUpValues = z.infer<typeof retailerSignUpSchema>
export type UserSignUpValues = z.infer<typeof userSignUpSchema>
export type SignInValues = z.infer<typeof signInSchema>

/** The request body the retailer sign-up endpoint takes. */
export function retailerPayload(values: RetailerSignUpValues) {
  return {
    organisation_name: values.organisationName,
    display_name: values.displayName,
    email: values.email,
    password: values.password,
    risk_profile: values.riskProfile,
  }
}

/** The request body the staff sign-up endpoint takes. */
export function userPayload(values: UserSignUpValues) {
  return {
    invite_code: values.inviteCode,
    display_name: values.displayName,
    email: values.email,
    password: values.password,
  }
}
