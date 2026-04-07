'use client'

import * as React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '#/lib/utils'
import {
  Combobox,
  ComboboxInput,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxEmpty,
} from '#/components/ui/combobox'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationPrevious,
  PaginationNext,
} from '#/components/ui/pagination'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AutocompleteOption = {
  value: string
  label: string
}

export type AutocompletePagination = {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export type AutocompleteProps = {
  /** Currently selected value (controlled) */
  value?: string
  /** Initial value for uncontrolled usage */
  defaultValue?: string
  /** Called when the user picks an option */
  onChange?: (value: string) => void
  /** Alias for onChange — kept for backward compat */
  onValueChange?: (value: string) => void
  /** Static list of options */
  options: AutocompleteOption[]
  /** Contextual noun shown in placeholder & empty state, e.g. "employee" */
  context?: string
  /** Optional server-side search callback (debounce externally) */
  onSearch?: (query: string) => void
  /** Optional pagination config */
  pagination?: AutocompletePagination
  /** Disable the control */
  disabled?: boolean
  /** Loading state (e.g. while fetching options) */
  loading?: boolean
  /** Render a custom item instead of the default label */
  renderItem?: (option: AutocompleteOption) => React.ReactNode
  /** Pass-through id for form field association */
  id?: string
  /** aria-invalid for form integration */
  'aria-invalid'?: boolean
  /** Additional className on the root input */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Autocomplete({
  value: valueProp,
  defaultValue = '',
  onChange,
  onValueChange,
  options,
  context = 'item',
  onSearch,
  pagination,
  disabled = false,
  loading = false,
  renderItem,
  id,
  'aria-invalid': ariaInvalid,
  className,
}: AutocompleteProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue)
  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  const handleChange = React.useCallback(
    (next: string) => {
      if (!isControlled) setInternalValue(next)
      onChange?.(next)
      onValueChange?.(next)
    },
    [isControlled, onChange, onValueChange],
  )

  const items = React.useMemo(() => options.map((o) => o), [options])

  const selectedOption = options.find((o) => o.value === value) ?? null

  return (
    <Combobox
      items={items}
      value={selectedOption}
      onValueChange={(item) => handleChange(item?.value ?? '')}
      itemToStringValue={(item) => item.value}
      itemToStringLabel={(item) => item.label}
      onInputValueChange={(inputVal) => onSearch?.(inputVal)}
      disabled={disabled}
    >
      <ComboboxInput
        id={id}
        placeholder={`Search ${context}...`}
        disabled={disabled}
        aria-invalid={ariaInvalid}
        className={cn(className)}
        showClear={!!value}
      />
      <ComboboxContent>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading...
          </div>
        ) : (
          <>
            <ComboboxEmpty>No {context} found.</ComboboxEmpty>
            <ComboboxList>
              {(item) => (
                <ComboboxItem key={item.value} value={item} className={'z-50'}>
                  {renderItem ? renderItem(item) : item.label}
                </ComboboxItem>
              )}
            </ComboboxList>
          </>
        )}

        {pagination && pagination.totalPages > 1 && (
          <div className="border-t px-1 py-1.5">
            <Pagination className="mx-0 justify-between">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={(e) => {
                      e.preventDefault()
                      if (pagination.currentPage > 1) {
                        pagination.onPageChange(pagination.currentPage - 1)
                      }
                    }}
                    className={cn(
                      'h-7 text-xs',
                      pagination.currentPage <= 1 &&
                        'pointer-events-none opacity-50',
                    )}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="px-2 text-xs text-muted-foreground">
                    {pagination.currentPage} / {pagination.totalPages}
                  </span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    onClick={(e) => {
                      e.preventDefault()
                      if (pagination.currentPage < pagination.totalPages) {
                        pagination.onPageChange(pagination.currentPage + 1)
                      }
                    }}
                    className={cn(
                      'h-7 text-xs',
                      pagination.currentPage >= pagination.totalPages &&
                        'pointer-events-none opacity-50',
                    )}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </ComboboxContent>
    </Combobox>
  )
}
