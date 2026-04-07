import { useState } from 'react'
import { Trash2, FolderOpen } from 'lucide-react'
import { toast } from 'sonner'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '#/components/ui/alert-dialog'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Field, FieldError, FieldLabel } from '#/components/ui/field'
import { Skeleton } from '#/components/ui/skeleton'
import { Separator } from '#/components/ui/separator'
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
} from '#/components/ui/empty'
import { formatDate } from '#/lib/utils'
import { ApiError } from '#/lib/api-client'
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  formatCategoryName,
} from '#/hooks/use-categories'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import type { CategoryItem } from '#/lib/models/types'

// ── Schema ────────────────────────────────────────────────────────────────────

const addCategorySchema = z.object({
  category_name: z.string().min(1, 'Category name is required'),
})

// ── Delete confirmation ───────────────────────────────────────────────────────

function DeleteCategoryDialog({
  category,
  onClose,
}: {
  category: CategoryItem | null
  onClose: () => void
}) {
  const deleteCategory = useDeleteCategory()

  const handleConfirm = () => {
    if (!category) return
    deleteCategory.mutate(category.category_id, {
      onSuccess: () => {
        toast.success(
          `Category '${formatCategoryName(category.category_name)}' deleted.`,
        )
        onClose()
      },
      onError: (err) => {
        if (err instanceof ApiError && err.status === 404) {
          toast.error('Category not found — it may have already been deleted.')
        } else {
          toast.error((err as Error).message || 'Failed to delete category.')
        }
        onClose()
      },
    })
  }

  return (
    <AlertDialog open={!!category} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete category?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete &apos;
            {category ? formatCategoryName(category.category_name) : ''}
            &apos;? Existing assets with this category will not be affected.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

// ── Category list ─────────────────────────────────────────────────────────────

function CategoryList({
  cursor,
  onNextPage,
  onPreviousPage,
  canGoPrevious,
  onDeleteRequest,
}: {
  cursor: string | undefined
  onNextPage: (nextCursor: string) => void
  onPreviousPage: () => void
  canGoPrevious: boolean
  onDeleteRequest: (cat: CategoryItem) => void
}) {
  const { data, isLoading, error } = useCategories({ cursor })

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="size-9 rounded-lg" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert-danger text-sm">
        {(error as Error).message || 'Failed to load categories.'}
      </div>
    )
  }

  if (!data?.items.length) {
    return (
      <Empty className="py-8 border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <FolderOpen className="size-5" />
          </EmptyMedia>
          <EmptyTitle>No categories yet</EmptyTitle>
          <EmptyDescription>
            Add your first category below to get started.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <div className="space-y-3">
      <div>
        {data.items.map((cat, index) => (
          <div key={cat.category_id}>
            {index > 0 && <Separator />}
            <div className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <span className="text-xs font-semibold">
                  {cat.category_name.charAt(0)}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {formatCategoryName(cat.category_name)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Added {formatDate(cat.created_at)}
                </p>
              </div>
              <Button
                variant="destructive"
                size="icon-sm"
                onClick={() => onDeleteRequest(cat)}
                aria-label={`Delete ${formatCategoryName(cat.category_name)}`}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {(canGoPrevious || (data.has_next_page ?? false)) && (
        <>
          <Separator />
          <div className="flex items-center justify-end text-xs text-muted-foreground">
            <div className="flex gap-1">
              <Button
                variant="outline"
                size="xs"
                disabled={!canGoPrevious}
                onClick={onPreviousPage}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="xs"
                disabled={!(data.has_next_page ?? false)}
                onClick={() => data.next_cursor && onNextPage(data.next_cursor)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ── Add category form ─────────────────────────────────────────────────────────

function AddCategoryForm() {
  const createCategory = useCreateCategory()

  const form = useForm({
    defaultValues: { category_name: '' },
    validators: {
      onSubmit: addCategorySchema,
    },
    onSubmit: async ({ value, formApi }) => {
      await new Promise<void>((resolve) => {
        createCategory.mutate(
          { category_name: value.category_name.trim() },
          {
            onSuccess: (data) => {
              toast.success(
                `Category '${formatCategoryName(data.category_name)}' created.`,
              )
              formApi.reset()
              resolve()
            },
            onError: (err) => {
              if (err instanceof ApiError && err.status === 409) {
                toast.error(err.message)
              } else {
                toast.error(
                  (err as Error).message || 'Failed to create category.',
                )
              }
              resolve()
            },
          },
        )
      })
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        e.stopPropagation()
        void form.handleSubmit()
      }}
      className="flex items-end gap-2"
    >
      <form.Field
        name="category_name"
        children={(field) => {
          const isInvalid =
            field.state.meta.isTouched && !field.state.meta.isValid
          return (
            <Field data-invalid={isInvalid} className="flex-1">
              <FieldLabel htmlFor={field.name}>Add new category</FieldLabel>
              <Input
                id={field.name}
                name={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
                aria-invalid={isInvalid}
                placeholder="e.g. Monitor, Printer, Headset"
              />
              {isInvalid && <FieldError errors={field.state.meta.errors} />}
            </Field>
          )
        }}
      />
      <form.Subscribe
        selector={(s) => s.canSubmit}
        children={(canSubmit) => (
          <Button
            type="submit"
            disabled={!canSubmit}
            loading={createCategory.isPending}
          >
            Add
          </Button>
        )}
      />
    </form>
  )
}

// ── Main dialog ───────────────────────────────────────────────────────────────

export interface ManageCategoriesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ManageCategoriesDialog({
  open,
  onOpenChange,
}: ManageCategoriesDialogProps) {
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
  } = useCursorPagination(10)
  const [categoryToDelete, setCategoryToDelete] = useState<CategoryItem | null>(
    null,
  )

  const handleOpenChange = (next: boolean) => {
    if (next) resetPagination()
    onOpenChange(next)
  }

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <DialogTitle>Manage Categories</DialogTitle>
            </div>
            <DialogDescription>
              Add or remove asset categories. Deleting a category does not
              affect existing assets.
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-y-auto -mx-1 px-1 max-h-[340px]">
            <CategoryList
              cursor={currentCursor}
              onNextPage={goToNextPage}
              onPreviousPage={goToPreviousPage}
              canGoPrevious={canGoPrevious}
              onDeleteRequest={setCategoryToDelete}
            />
          </div>

          <DialogFooter className="flex-col gap-0 sm:flex-col">
            <AddCategoryForm />
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DeleteCategoryDialog
        category={categoryToDelete}
        onClose={() => setCategoryToDelete(null)}
      />
    </>
  )
}
