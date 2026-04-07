import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { Label } from '#/components/ui/label'
import {
  Autocomplete,
  type AutocompleteOption,
} from '#/components/ui/autocomplete'
import { useAssignAsset } from '#/hooks/use-assets'
import { useDebounce } from '#/hooks/use-debounce'
import { apiClient, ApiError } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ListUsersResponse } from '#/lib/models/types'

type AssignAssetModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
}

export function AssignAssetModal({
  open,
  onOpenChange,
  assetId,
}: AssignAssetModalProps) {
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const [selectedEmployeeName, setSelectedEmployeeName] = useState('')
  const [notes, setNotes] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  // Ref tracks whether an employee is selected — updated synchronously so
  // handleSearch (fired by onInputValueChange) can skip the refetch that
  // happens when the Combobox sets the input text to the selected label.
  const hasSelectionRef = useRef(false)

  const debouncedSearch = useDebounce(searchQuery, 400)

  const assignAsset = useAssignAsset(assetId)

  // Reset form state when dialog opens/closes
  useEffect(() => {
    setSelectedEmployeeId('')
    setSelectedEmployeeName('')
    setNotes('')
    setSearchQuery('')
    hasSelectionRef.current = false
    assignAsset.reset()
  }, [open])

  const queryParams = {
    filters: {
      name: debouncedSearch || undefined,
      status: 'active' as const,
      role: 'employee' as const,
    },
  }

  const employeesQuery = useQuery({
    queryKey: queryKeys.users.list(queryParams),
    queryFn: async () => {
      const params = new URLSearchParams({
        status: 'active',
        role: 'employee',
        ...(debouncedSearch && { name: debouncedSearch }),
      })
      return apiClient<ListUsersResponse>(`/users?${params.toString()}`)
    },
    enabled: open,
    staleTime: 60_000,
  })

  const options: AutocompleteOption[] =
    employeesQuery.data?.items.map((user) => ({
      value: user.user_id,
      label: user.fullname,
    })) ?? []

  const handleSearch = useCallback((query: string) => {
    // The Combobox fires onInputValueChange with the selected label right
    // before onValueChange. Use the ref (synchronous) to skip that update.
    if (hasSelectionRef.current) return
    setSearchQuery(query)
  }, [])

  const handleEmployeeChange = useCallback(
    (value: string) => {
      hasSelectionRef.current = !!value
      setSelectedEmployeeId(value)
      const match = options.find((o) => o.value === value)
      setSelectedEmployeeName(match?.label ?? '')
    },
    [options],
  )

  const handleConfirm = useCallback(() => {
    if (!selectedEmployeeId) return

    assignAsset.mutate(
      {
        employee_id: selectedEmployeeId,
        notes: notes.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          toast.success(
            `Asset assigned to ${selectedEmployeeName}. Handover form generated and email sent.`,
          )
          if (data.presigned_url) {
            window.open(data.presigned_url, '_blank')
          }
          onOpenChange(false)
        },
        onError: (err) => {
          if (err instanceof ApiError) {
            toast.error(err.message)
          } else {
            toast.error('An unexpected error occurred. Please try again.')
          }
        },
      },
    )
  }, [
    selectedEmployeeId,
    selectedEmployeeName,
    notes,
    assignAsset,
    onOpenChange,
  ])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign Asset</DialogTitle>
          <DialogDescription>
            Select an employee to assign this asset to. A handover form will be
            generated and emailed to the employee.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="employee-search">Employee</Label>
            <Autocomplete
              id="employee-search"
              value={selectedEmployeeId}
              onChange={handleEmployeeChange}
              options={options}
              context="employee"
              onSearch={handleSearch}
              loading={employeesQuery.isLoading}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="assign-notes">Notes (optional)</Label>
            <Textarea
              id="assign-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about this assignment..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            disabled={!selectedEmployeeId || assignAsset.isPending}
            loading={assignAsset.isPending}
            onClick={handleConfirm}
          >
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
