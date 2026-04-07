import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { confirmSignIn } from 'aws-amplify/auth'
import { z } from 'zod'
import { useForm } from '@tanstack/react-form'
import { getRedirectTarget, isAuthenticated } from '../lib/auth'
import { buildSeoHead, type SeoPageInput } from '../lib/seo'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { toast } from 'sonner'
import { ShieldCheck } from 'lucide-react'

const NEW_PASSWORD_SEO = {
  title: 'Set New Password',
  description:
    'Create a new secure password for your Gadget Management System account. Required on first login or after a password reset request.',
  path: '/new-password',
} satisfies SeoPageInput

export const Route = createFileRoute('/new-password')({
  validateSearch: (
    search: Record<string, unknown>,
  ): { redirectTo?: string } => ({
    redirectTo:
      typeof search.redirectTo === 'string' ? search.redirectTo : undefined,
  }),
  beforeLoad: async ({ search }) => {
    if (await isAuthenticated()) {
      throw redirect({
        href: getRedirectTarget(search.redirectTo),
      })
    }
  },
  component: NewPasswordPage,
  head: () => buildSeoHead(NEW_PASSWORD_SEO),
})

const newPasswordSchema = z.object({
  newPassword: z.string().min(8, 'Password must be at least 8 characters long'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
})

function NewPasswordPage() {
  const navigate = useNavigate()
  const { redirectTo } = Route.useSearch()

  const form = useForm({
    defaultValues: {
      newPassword: '',
      confirmPassword: '',
    },
    validators: {
      onSubmit: newPasswordSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        const { isSignedIn, nextStep } = await confirmSignIn({
          challengeResponse: value.newPassword,
        })

        if (isSignedIn) {
          toast.success('Password updated successfully')
          void navigate({
            href: getRedirectTarget(redirectTo),
            replace: true,
          })
        } else {
          toast.error(`Sign in step: ${nextStep?.signInStep}`)
        }
      } catch (error: any) {
        console.error('Password reset error:', error)
        toast.error(
          error.message || 'Failed to update password. Please try again.',
        )
      }
    },
  })

  return (
    <main className="mx-auto grid min-h-screen w-full max-w-5xl place-items-center px-4 py-10 bg-background text-foreground">
      <section className="grid w-full gap-8 rounded-3xl border bg-card p-6 shadow-lg md:grid-cols-[1.1fr_0.9fr] md:p-10">
        <div className="hidden rounded-2xl bg-muted p-8 md:flex flex-col">
          <div className="flex items-center gap-2 text-primary mb-4">
            <ShieldCheck className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-[0.25em]">
              Security Update
            </p>
          </div>
          <h1 className="font-sans text-4xl leading-tight text-foreground font-bold tracking-tight">
            Set up your permanent password.
          </h1>
          <p className="mt-5 text-sm leading-7 text-muted-foreground grow">
            Your account requires a new password before you can access the
            system. Please choose a strong, unique password to ensure the
            security of your Gadget Management System workspace.
          </p>
          <div className="pt-8 border-t border-border mt-8">
            <p className="text-xs text-muted-foreground">
              © 2026 GadgetAdmin System Management. All rights reserved.
            </p>
          </div>
        </div>

        <div className="flex flex-col justify-center">
          <Card className="border-none shadow-none bg-transparent">
            <CardHeader className="px-0 pt-0">
              <CardTitle className="text-2xl font-bold tracking-tight">
                Change Password
              </CardTitle>
              <CardDescription>
                Create a new password for your account
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  void form.handleSubmit()
                }}
              >
                <FieldGroup>
                  <form.Field
                    name="newPassword"
                    children={(field) => {
                      const isInvalid =
                        field.state.meta.isTouched && !field.state.meta.isValid
                      return (
                        <Field data-invalid={isInvalid}>
                          <FieldLabel htmlFor={field.name}>
                            New Password
                          </FieldLabel>
                          <Input
                            id={field.name}
                            name={field.name}
                            type="password"
                            value={field.state.value}
                            onBlur={field.handleBlur}
                            onChange={(e) => field.handleChange(e.target.value)}
                            aria-invalid={isInvalid}
                            placeholder="••••••••"
                          />
                          {isInvalid && (
                            <FieldError errors={field.state.meta.errors} />
                          )}
                        </Field>
                      )
                    }}
                  />

                  <form.Field
                    name="confirmPassword"
                    validators={{
                      onChangeListenTo: ['newPassword'],
                      onChange: ({ value, fieldApi }) => {
                        if (
                          value &&
                          value !== fieldApi.form.getFieldValue('newPassword')
                        ) {
                          return { message: "Passwords don't match" }
                        }
                        return undefined
                      },
                    }}
                    children={(field) => {
                      const isInvalid =
                        field.state.meta.isTouched && !field.state.meta.isValid
                      return (
                        <Field data-invalid={isInvalid}>
                          <FieldLabel htmlFor={field.name}>
                            Confirm Password
                          </FieldLabel>
                          <Input
                            id={field.name}
                            name={field.name}
                            type="password"
                            value={field.state.value}
                            onBlur={field.handleBlur}
                            onChange={(e) => field.handleChange(e.target.value)}
                            aria-invalid={isInvalid}
                            placeholder="••••••••"
                          />
                          {isInvalid && (
                            <FieldError errors={field.state.meta.errors} />
                          )}
                        </Field>
                      )
                    }}
                  />
                </FieldGroup>

                <form.Subscribe
                  selector={(state) =>
                    [state.canSubmit, state.isSubmitting] as const
                  }
                  children={([canSubmit, isSubmitting]) => (
                    <Button
                      type="submit"
                      className="w-full font-semibold mt-4"
                      disabled={!canSubmit}
                      loading={isSubmitting}
                    >
                      Update Password
                    </Button>
                  )}
                />
              </form>
            </CardContent>
            <CardFooter className="px-0 pb-0 justify-center">
              <p className="text-xs text-muted-foreground text-center">
                Make sure it's at least 8 characters long.
              </p>
            </CardFooter>
          </Card>
        </div>
      </section>
    </main>
  )
}
