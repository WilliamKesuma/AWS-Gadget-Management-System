import { Link, useRouter } from '@tanstack/react-router'
import { Home, ArrowLeft } from 'lucide-react'
import { Button } from '#/components/ui/button'

export function NotFoundPage() {
  const router = useRouter()

  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6 py-20">
      {/* decorative blob */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <div className="absolute left-1/2 top-1/3 h-[480px] w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/6 blur-[120px]" />
      </div>

      <div className="flex w-full max-w-md flex-col items-center gap-6 text-center">
        {/* large 404 */}
        <p className="select-none font-bold text-[7rem] leading-none tracking-tighter text-border">
          404
        </p>

        {/* heading */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Page not found
          </h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            The page you're looking for doesn't exist or may have been moved.
            Check the URL and try again.
          </p>
        </div>

        {/* actions */}
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <Button variant="default" className="flex-1 gap-2" asChild>
            <Link to="/">
              <Home className="h-4 w-4" />
              Go to dashboard
            </Link>
          </Button>
          <Button
            variant="outline"
            className="flex-1 gap-2"
            onClick={() => router.history.back()}
          >
            <ArrowLeft className="h-4 w-4" />
            Go back
          </Button>
        </div>
      </div>
    </main>
  )
}
