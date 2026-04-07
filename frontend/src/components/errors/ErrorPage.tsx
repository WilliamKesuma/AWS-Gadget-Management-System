import {
  Link,
  useRouter,
  type ErrorComponentProps,
} from '@tanstack/react-router'
import { AlertTriangle, RotateCcw, Home } from 'lucide-react'
import { Button } from '#/components/ui/button'

export function ErrorPage({ error, reset }: ErrorComponentProps) {
  const router = useRouter()

  const message =
    error instanceof Error ? error.message : 'An unexpected error occurred.'

  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6 py-20">
      {/* decorative blurred blob */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <div className="absolute left-1/2 top-1/3 h-[480px] w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-destructive/8 blur-[120px]" />
      </div>

      <div className="flex w-full max-w-md flex-col items-center gap-6 text-center">
        {/* icon badge */}
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-destructive/20 bg-destructive/8 shadow-sm">
          <AlertTriangle
            className="h-8 w-8 text-destructive"
            strokeWidth={1.5}
          />
        </div>

        {/* heading */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Something went wrong
          </h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            The page encountered an error and couldn't be displayed. You can try
            again or return to the dashboard.
          </p>
        </div>

        {/* error detail */}
        {message && (
          <div className="w-full rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-left">
            <p className="font-mono text-xs leading-relaxed text-destructive/80 break-all">
              {message}
            </p>
          </div>
        )}

        {/* actions */}
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <Button
            variant="default"
            className="flex-1 gap-2"
            onClick={() => {
              reset()
              router.invalidate()
            }}
          >
            <RotateCcw className="h-4 w-4" />
            Try again
          </Button>
          <Button variant="outline" className="flex-1 gap-2" asChild>
            <Link to="/">
              <Home className="h-4 w-4" />
              Go to dashboard
            </Link>
          </Button>
        </div>
      </div>
    </main>
  )
}
