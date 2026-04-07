import { Link, useRouter } from '@tanstack/react-router'
import { Home, ArrowLeft } from 'lucide-react'
import { Button } from '#/components/ui/button'

export function UnauthorizedPage() {
  const router = useRouter()

  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6 py-20">
      <div className="flex w-full max-w-md flex-col items-center gap-6 text-center">
        {/* large 403 */}
        <p className="select-none font-bold text-[7rem] leading-none tracking-tighter text-border">
          403
        </p>

        {/* heading */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Access denied
          </h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            You don't have permission to view this page. Contact your
            administrator if you believe this is a mistake.
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
