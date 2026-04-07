import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { resetPassword, confirmResetPassword } from 'aws-amplify/auth'
import { z } from 'zod'
import { useForm } from '@tanstack/react-form'
import { buildSeoHead, type SeoPageInput } from '../lib/seo'
import {
  Card,
  CardContent,
  CardDescription,
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
import { ShieldCheck, ArrowLeft } from 'lucide-react'

const FORGOT_PASSWORD_SEO = {
  title: 'Forgot Password',
  description:
    'Reset your Gadget Management System password. Enter your username or email to receive a verification code and regain access to your workspace.',
  path: '/forgot-password',
} satisfies SeoPageInput

export const Route = createFileRoute('/forgot-password')({
  validateSearch: (
    search: Record<string, unknown>,
  ): { redirectTo?: string } => ({
    redirectTo:
      typeof search.redirectTo === 'string' ? search.redirectTo : undefined,
  }),
  component: ForgotPasswordPage,
  head: () => buildSeoHead(FORGOT_PASSWORD_SEO),
})

const requestSchema = z.object({
  username: z.string().min(1, 'Email or username is required'),
})

const confirmSchema = z.object({
  code: z.string().min(1, 'Verification code is required'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters long'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
})

function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { redirectTo } = Route.useSearch()
  const [step, setStep] = useState<1 | 2>(1)
  const [username, setUsername] = useState('')

  const requestForm = useForm({
    defaultValues: { username: '' },
    validators: { onSubmit: requestSchema },
    onSubmit: async ({ value }) => {
      try {
        const output = await resetPassword({ username: value.username })
        setUsername(value.username)
        if (
          output.nextStep.resetPasswordStep ===
          'CONFIRM_RESET_PASSWORD_WITH_CODE'
        ) {
          setStep(2)
          toast.success('Verification code sent')
        } else if (output.nextStep.resetPasswordStep === 'DONE') {
          toast.success('Password successfully reset')
          void navigate({ to: '/login', search: { redirectTo } })
        }
      } catch (error: any) {
        toast.error(error.message || 'Failed to request reset.')
      }
    },
  })

  const confirmForm = useForm({
    defaultValues: { code: '', newPassword: '', confirmPassword: '' },
    validators: { onSubmit: confirmSchema },
    onSubmit: async ({ value }) => {
      try {
        await confirmResetPassword({
          username,
          confirmationCode: value.code,
          newPassword: value.newPassword,
        })
        toast.success('Password reset successfully')
        void navigate({ to: '/login', search: { redirectTo } })
      } catch (error: any) {
        toast.error(error.message || 'Failed to reset password.')
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
              Account Recovery
            </p>
          </div>
          <h1 className="font-sans text-4xl leading-tight text-foreground font-bold tracking-tight">
            Regain access to your workspace.
          </h1>
          <p className="mt-5 text-sm leading-7 text-muted-foreground grow">
            Forgot your password? No worries. Request a code to safely reset it
            and get back to managing devices. Your security comes first.
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
              <div className="mb-4 w-fit">
                <Link
                  to="/login"
                  search={{ redirectTo }}
                  className="flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" /> Back to sign in
                </Link>
              </div>
              <CardTitle className="text-2xl font-bold tracking-tight">
                {step === 1 ? 'Reset Password' : 'Confirm Reset'}
              </CardTitle>
              <CardDescription>
                {step === 1
                  ? 'Enter your username or email to receive a recovery code.'
                  : 'Enter the verification code sent to you and your new password.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              {step === 1 ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    void requestForm.handleSubmit()
                  }}
                >
                  <FieldGroup>
                    <requestForm.Field
                      name="username"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor={field.name}>
                              Email or username
                            </FieldLabel>
                            <Input
                              id={field.name}
                              name={field.name}
                              value={field.state.value}
                              onBlur={field.handleBlur}
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
                              aria-invalid={isInvalid}
                              placeholder="you@company.com"
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )
                      }}
                    />
                  </FieldGroup>
                  <requestForm.Subscribe
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
                        Send Code
                      </Button>
                    )}
                  />
                </form>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    void confirmForm.handleSubmit()
                  }}
                >
                  <FieldGroup>
                    <confirmForm.Field
                      name="code"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor={field.name}>
                              Verification Code
                            </FieldLabel>
                            <Input
                              id={field.name}
                              name={field.name}
                              value={field.state.value}
                              onBlur={field.handleBlur}
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
                              aria-invalid={isInvalid}
                              placeholder="123456"
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )
                      }}
                    />
                    <confirmForm.Field
                      name="newPassword"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
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
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
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
                    <confirmForm.Field
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
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
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
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
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
                  <confirmForm.Subscribe
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
                        Reset Password
                      </Button>
                    )}
                  />
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  )
}
