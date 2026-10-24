import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'

import { setOrgId } from '@/api/client'
import { describeAuthFailure, signUpRetailer, type Account } from '@/api/auth'
import { Button, Callout, Field, inputClass, selectClass } from '@/components/ui'
import { retailerPayload, retailerSignUpSchema, type RetailerSignUpValues } from '@/auth/schemas'
import { AuthLayout } from './AuthLayout'

/**
 * A retailer creates its organisation (F11.1).
 *
 * The account that comes back is the administrator, and the organisation's
 * code is shown once, because the administrator will give it to the staff who
 * join. The code is also the organisation's identifier, which is how the shop
 * window and the console find its stock.
 */
export function RetailerSignUpPage() {
  const navigate = useNavigate()
  const [account, setAccount] = useState<Account | null>(null)

  const form = useForm<RetailerSignUpValues>({
    resolver: zodResolver(retailerSignUpSchema),
    mode: 'onTouched',
    defaultValues: {
      organisationName: '',
      displayName: '',
      email: '',
      password: '',
      riskProfile: 'balanced',
    },
  })
  const { register, handleSubmit, formState } = form
  const { errors } = formState

  const mutation = useMutation({
    mutationFn: (values: RetailerSignUpValues) => signUpRetailer(retailerPayload(values)),
    onSuccess: (created) => {
      setOrgId(created.org_id)
      setAccount(created)
    },
  })

  if (account) {
    return (
      <AuthLayout title="Your retailer is ready" lead={`${account.organisation_name} is set up. You are its administrator.`}>
        <div className="space-y-5">
          <div className="rounded-xl bg-background/60 p-4 ring-1 ring-border">
            <p className="text-xs font-medium text-muted-foreground">Your retailer code</p>
            <code className="mt-2 block break-all font-mono text-sm" data-testid="retailer-code">
              {account.org_id}
            </code>
            <p className="mt-3 text-xs text-muted-foreground">
              Give this to the people who will inspect for you. They need it to join.
            </p>
          </div>
          <Button className="w-full" size="lg" onClick={() => navigate('/')}>
            Open the console
            <ArrowRight aria-hidden="true" />
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Set up your retailer"
      lead="You will be its administrator. You can invite your staff afterwards."
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
          <Callout tone="warning" title="The retailer could not be made">
            <p>{describeAuthFailure(mutation.error)}</p>
          </Callout>
        )}

        <Field label="Business name" required error={errors.organisationName?.message}>
          {({ id, describedBy }) => (
            <input
              id={id}
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.organisationName)}
              autoComplete="organization"
              className={inputClass}
              {...register('organisationName')}
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

        <Field
          label="How much risk should the engine take?"
          hint="Balanced is the usual choice. Conservative prefers certainty; aggressive prefers the bigger return."
        >
          {({ id, describedBy }) => (
            <select id={id} aria-describedby={describedBy} className={selectClass} {...register('riskProfile')}>
              <option value="conservative">Conservative</option>
              <option value="balanced">Balanced</option>
              <option value="aggressive">Aggressive</option>
            </select>
          )}
        </Field>

        <Button type="submit" className="w-full" size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? 'Setting up…' : 'Create the retailer'}
        </Button>
      </form>
    </AuthLayout>
  )
}
