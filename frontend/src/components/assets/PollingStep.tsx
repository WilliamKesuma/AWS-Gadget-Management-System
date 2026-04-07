import { useEffect, useState } from 'react'
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  ClockIcon,
  SparklesIcon,
} from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Spinner } from '#/components/ui/spinner'
import { useScanJob } from '#/hooks/use-assets'
import { ApiError } from '#/lib/api-client'

// ─── Types ───────────────────────────────────────────────────────────────────

type ProgressState = 'pending' | 'in-progress' | 'completed'

const STEPS = [
  'Analyzing Invoice',
  'Processing Photos',
  'Validating Serial Numbers',
] as const

// ─── Friendly error messages ─────────────────────────────────────────────────

const TEXTRACT_ERROR_MAP: Record<string, string> = {
  'Textract job FAILED':
    'The document could not be processed. Please ensure the invoice is a clear, readable PDF or image.',
  UnsupportedDocumentException:
    'The uploaded file format is not supported. Please use a PDF, JPEG, PNG, or TIFF file.',
  BadDocumentException:
    'The document appears to be corrupted or unreadable. Please try uploading a different file.',
  DocumentTooLargeException:
    'The document is too large to process. Please reduce the file size and try again.',
  InvalidS3ObjectException:
    'The uploaded file could not be found. Please try uploading again.',
  ProvisionedThroughputExceededException:
    'The service is currently busy. Please wait a moment and try again.',
  ThrottlingException: 'Too many requests. Please wait a moment and try again.',
  LimitExceededException:
    'The service has reached its processing limit. Please try again later.',
  InternalServerError:
    'An unexpected error occurred on the server. Please try again.',
}

function getFriendlyError(failureReason?: string): string {
  if (!failureReason)
    return 'An unexpected error occurred while processing your document.'

  for (const [key, message] of Object.entries(TEXTRACT_ERROR_MAP)) {
    if (failureReason.includes(key)) return message
  }

  return `Document processing failed: ${failureReason}`
}

// ─── PollingStep ─────────────────────────────────────────────────────────────

export interface PollingStepProps {
  scanJobId: string
  uploadSessionId: string
  onCancel: () => void
  onRetry: () => void
}

export function PollingStep({
  scanJobId,
  uploadSessionId,
  onCancel,
  onRetry,
}: PollingStepProps) {
  const navigate = useNavigate()
  const [stepStates, setStepStates] = useState<ProgressState[]>([
    'in-progress',
    'pending',
    'pending',
  ])
  const [errorMessage, setErrorMessage] = useState<string>()
  const hasFailed = !!errorMessage

  const { data: scanResult, error: scanError } = useScanJob(scanJobId)

  // Task 5.2 — Animated progress cycling
  useEffect(() => {
    const interval = setInterval(() => {
      setStepStates((prev) => {
        const inProgressIdx = prev.indexOf('in-progress')
        if (inProgressIdx === -1) {
          // All completed — reset to start
          return ['in-progress', 'pending', 'pending']
        }
        const next = [...prev] as ProgressState[]
        next[inProgressIdx] = 'completed'
        const nextIdx = inProgressIdx + 1
        if (nextIdx < next.length) {
          next[nextIdx] = 'in-progress'
        } else {
          // Last step just completed — reset on next tick
          return ['in-progress', 'pending', 'pending']
        }
        return next
      })
    }, 1500)
    return () => clearInterval(interval)
  }, [])

  // Task 5.4 — React to scan result status
  useEffect(() => {
    if (scanResult?.status === 'COMPLETED') {
      void navigate({
        to: '/assets/new',
        search: {
          scan_job_id: scanJobId,
          upload_session_id: uploadSessionId,
          ready: 1,
        },
        state: { extracted_fields: scanResult.extracted_fields } as Record<
          string,
          unknown
        >,
      })
    } else if (scanResult?.status === 'SCAN_FAILED') {
      setErrorMessage(getFriendlyError(scanResult.failure_reason))
    }
  }, [scanResult?.status])

  // Task 5.4 — React to network/query errors
  useEffect(() => {
    if (scanError) {
      if (
        scanError instanceof ApiError &&
        scanError.status === 422 &&
        scanError.failureReason
      ) {
        setErrorMessage(getFriendlyError(scanError.failureReason))
      } else {
        const msg =
          scanError instanceof ApiError
            ? scanError.message
            : 'A network error occurred. Please check your connection and try again.'
        setErrorMessage(msg)
      }
    }
  }, [scanError])

  // Stop the animation when an error occurs
  useEffect(() => {
    if (!hasFailed) return
    setStepStates(['pending', 'pending', 'pending'])
  }, [hasFailed])

  if (hasFailed) {
    return (
      <div className="flex flex-col gap-6">
        {/* Error header */}
        <div className="flex flex-col items-center gap-4 text-center">
          <h2 className="text-xl font-semibold">Extraction Failed</h2>

          <div className="flex size-20 items-center justify-center rounded-full bg-danger-subtle">
            <AlertTriangleIcon className="size-8 text-danger" />
          </div>

          <p className="text-sm text-muted-foreground">{errorMessage}</p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <Button className="w-full" onClick={onRetry}>
            Try Again
          </Button>
          <Button
            variant="outline"
            className="w-full text-destructive hover:text-destructive"
            onClick={onCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Task 5.1 — Header */}
      <div className="flex flex-col items-center gap-4 text-center">
        <h2 className="text-xl font-semibold">Extracting Data...</h2>

        {/* Circular spinner with sparkles icon */}
        <div className="relative flex size-20 items-center justify-center">
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-border border-t-info" />
          <SparklesIcon className="size-8 text-info" />
        </div>

        <p className="text-sm text-muted-foreground">
          Our AI is analyzing your documents to pre-fill the asset details.
        </p>
      </div>

      {/* Task 5.2 — Animated progress card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Extraction Progress
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {STEPS.map((label, i) => {
            const state = stepStates[i]
            return (
              <div key={label} className="flex items-center gap-3">
                {state === 'pending' && (
                  <ClockIcon className="size-5 shrink-0 text-muted-foreground" />
                )}
                {state === 'in-progress' && (
                  <Spinner className="size-5 shrink-0 text-info" />
                )}
                {state === 'completed' && (
                  <CheckCircle2Icon className="size-5 shrink-0 text-info" />
                )}
                <span className="text-sm">{label}</span>
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Task 5.6 — Footer */}
      <Button
        variant="outline"
        className="w-full text-destructive hover:text-destructive"
        onClick={onCancel}
      >
        Cancel
      </Button>
    </div>
  )
}
