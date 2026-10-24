import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'

import { setOrgId } from '@/api/client'
import { describeAuthFailure, signUpUser, type Account } from '@/api/auth'
import { Button, Callout, Field, inputClass } from '@/components/ui'
import { userPayload, userSignUpSchema, type UserSignUpValues } from '@/auth/schemas'
import { AuthLayout } from './AuthLayout'

/**
 * A person joins a retailer as an inspector (F11.1).
 *
 * The retailer's code is what connects the person to the right stock. A person
 * with the wrong code is told so, and nothing about the retailer is shown
 * before the code is recognised.
 */
export function UserSignUpPage() {
  const navigate = useNavigate()
  const [account, setAccount] = useState<Account | null>(null)

  const form = useForm<UserSignUpValues>({
    resolver: zodResolver(userSignUpSchema),
    mode: 'onTouched',
    defaultValues: { inviteCode: '', displayName: '', email: '', password: '' },
  })
  const { register, handleSubmit, formState } = form
  const { errors } = formState

  const mutation = useMutation({
    mutationFn: (values: UserSignUpValues) => signUpUser(userPayload(values)),
    onSuccess: (created) => {
      setOrgId(created.org_id)
      setAccount(created)
    },
  })

  if (account) {
    return (
      <AuthLayout
        title="Welcome aboard"
        lead={`Your account is ready. You joined ${account.organisation_name ?? 'the retailer'} as an inspector.`}
      >
        <Button className="w-full" size="lg" onClick={() => navigate('/')}>
          Open the console
          <ArrowRight aria-hidden="true" />
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Join your retailer"
      lead="Use the code your retailer gave you. You will be an inspector."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/signin" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form className="space-y-5" noValidate onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        {mutation.isError && (
          <Callout tone="warning" title="You could not join">
            <p>{describeAuthFailure(mutation.error)}</p>
          </Callout>
        )}

        <Field label="Retailer code" required error={errors.inviteCode?.message}>
          {({ id, describedBy }) => (
            <input
              id={id}
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.inviteCode)}
              autoComplete="off"
              spellCheck={false}
              className={`${inputClass} font-mono`}
              {...register('inviteCode')}
            />
          )}
        </Field>

        <Field label="Your name" required error={errors.displayName?.message}>
          {({ id, describedBy }) => (
            <input
              id={id}
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.displayName)}
              autoComplete="name"
              className={inputClass}
              {...register('displayName')}
            />
          )}
        </Field>

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

        <Field
          label="Password"
          required
          hint="At least ten characters, with a letter and a number."
          error={errors.password?.message}
        >
          {({ id, describedBy }) => (
            <input
              id={id}
              type="password"
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.password)}
              autoComplete="new-password"
              className={inputClass}
              {...register('password')}
            />
          )}
        </Field>

        <Button type="submit" className="w-full" size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? 'Joining…' : 'Join the retailer'}
        </Button>
      </form>
    </AuthLayout>
  )
}
