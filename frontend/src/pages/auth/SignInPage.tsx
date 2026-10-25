import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'

import { setOrgId } from '@/api/client'
import { describeAuthFailure, signIn } from '@/api/auth'
import { Button, Callout, Field, inputClass } from '@/components/ui'
import { signInSchema, type SignInValues } from '@/auth/schemas'
import { AuthLayout } from './AuthLayout'

/**
 * Sign in to the console (F11.1).
 *
 * A wrong email and a wrong password are reported in the same words, so the
 * form does not say which of the two addresses have accounts.
 */
export function SignInPage() {
  const navigate = useNavigate()

  const form = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    mode: 'onTouched',
    defaultValues: { email: '', password: '' },
  })
  const { register, handleSubmit, formState } = form
  const { errors } = formState

  const mutation = useMutation({
    mutationFn: (values: SignInValues) => signIn({ email: values.email, password: values.password }),
    onSuccess: (account) => {
      setOrgId(account.org_id)
      navigate('/')
    },
  })

  return (
    <AuthLayout
      title="Sign in"
      lead="Use the email address and password you signed up with."
      footer={
        <div className="space-y-2">
          <p>
            New here?{' '}
            <Link to="/signup" className="font-medium text-foreground underline-offset-4 hover:underline">
              Create an account
            </Link>
          </p>
          <p>
            <Link to="/welcome" className="font-medium text-foreground underline-offset-4 hover:underline">
              See how it works
            </Link>
          </p>
        </div>
      }
    >
      <form className="space-y-5" noValidate onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        {mutation.isError && (
          <Callout tone="warning" title="You could not sign in">
            <p>{describeAuthFailure(mutation.error)}</p>
          </Callout>
        )}

        <Field label="Email" required error={errors.email?.message}>
          {({ id, describedBy }) => (
            <input
              id={id}
              type="email"
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.email)}
              autoComplete="email"
              className={inputClass}
              {...register('email')}
            />
          )}
        </Field>

        <Field label="Password" required error={errors.password?.message}>
          {({ id, describedBy }) => (
            <input
              id={id}
              type="password"
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.password)}
              autoComplete="current-password"
              className={inputClass}
              {...register('password')}
            />
          )}
        </Field>

        <Button type="submit" className="w-full" size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthLayout>
  )
}
