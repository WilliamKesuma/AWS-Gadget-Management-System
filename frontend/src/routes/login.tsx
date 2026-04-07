import {
  createFileRoute,
  redirect,
  useNavigate,
  Link,
} from '@tanstack/react-router'
import { signIn } from 'aws-amplify/auth'
import { z } from 'zod'
import { useForm } from '@tanstack/react-form'
import {
  getRedirectTarget,
  getMissingAuthConfig,
  isAuthenticated,
} from '../lib/auth'
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

const LOGIN_SEO = {
  title: 'Sign In',
  description:
    'Sign in to the Gadget Management System to access inventory tracking, asset assignments, maintenance workflows, and lifecycle management tools.',
  path: '/login',
} satisfies SeoPageInput

export const Route = createFileRoute('/login')({
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
  component: LoginPage,
  head: () => buildSeoHead(LOGIN_SEO),
})

const loginSchema = z.object({
  username: z.string().min(1, 'Email or username is required'),
  password: z.string().min(1, 'Password is required'),
})

function LoginPage() {
  const navigate = useNavigate()
  const { redirectTo } = Route.useSearch()
  const missingConfig = getMissingAuthConfig()

  const form = useForm({
    defaultValues: {
      username: '',
      password: '',
    },
    validators: {
      onSubmit: loginSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        const { isSignedIn, nextStep } = await signIn({
          username: value.username,
          password: value.password,
          options: {
            authFlowType: 'USER_PASSWORD_AUTH',
          },
        })

        if (isSignedIn) {
          toast.success('Successfully signed in')
          void navigate({
            href: getRedirectTarget(redirectTo),
            replace: true,
          })
        } else {
          if (
            nextStep?.signInStep ===
            'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED'
          ) {
            toast.info('Please set a new password to continue.')
            void navigate({
              to: '/new-password',
              search: { redirectTo },
            })
          } else {
            toast.error(`Sign in step: ${nextStep?.signInStep}`)
          }
        }
      } catch (error: any) {
        console.error('Sign in error:', error)
        toast.error(
          error.message || 'Failed to sign in. Please check your credentials.',
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
              Secure access
            </p>
          </div>
          <h1 className="font-sans text-4xl leading-tight text-foreground font-bold tracking-tight">
            Manage every gadget with one trusted login.
          </h1>
          <p className="mt-5 text-sm leading-7 text-muted-foreground grow">
            Access the centralized Gadget Management System to monitor
            inventory, track repairs, and manage users. Our secure
            authentication ensures data integrity across the organization.
          </p>
          <div className="pt-8 border-t border-border mt-8">
            <p className="text-xs text-muted-foreground">
              © 2026 GadgetAdmin System Management. All rights reserved.
            </p>
          </div>
        </div>

        <div className="flex flex-col justify-center">
          {missingConfig.length > 0 ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
              Missing auth env config: {missingConfig.join(', ')}
            </div>
          ) : (
            <Card className="border-none shadow-none bg-transparent">
              <CardHeader className="px-0 pt-0">
                <CardTitle className="text-2xl font-bold tracking-tight">
                  Sign in
                </CardTitle>
                <CardDescription>
                  Enter your credentials to access your workspace
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

                    <form.Field
                      name="password"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
                        return (
                          <Field data-invalid={isInvalid}>
                            <div className="flex items-center justify-between">
                              <FieldLabel htmlFor={field.name}>
                                Password
                              </FieldLabel>
                              <Link
                                to="/forgot-password"
                                search={{ redirectTo }}
                                className="text-sm font-normal text-muted-foreground hover:text-primary transition-colors"
                              >
                                Forgot password?
                              </Link>
                            </div>
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
                        Sign in
                      </Button>
                    )}
                  />
                </form>
              </CardContent>
              <CardFooter className="px-0 pb-0 justify-center">
                <p className="text-xs text-muted-foreground text-center">
                  Secure Cognito sign-in for internal users.
                </p>
              </CardFooter>
            </Card>
          )}
        </div>
      </section>
    </main>
  )
}
