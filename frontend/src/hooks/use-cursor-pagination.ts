import { useState, useCallback } from 'react'

export type CursorPaginationState = {
    currentCursor: string | undefined
    cursorStack: string[]
    pageSize: number
}

export type CursorPaginationActions = {
    goToNextPage: (nextCursor: string) => void
    goToPreviousPage: () => void
    resetPagination: () => void
    canGoPrevious: boolean
}

export function useCursorPagination(pageSize: number = 10) {
    const [cursorStack, setCursorStack] = useState<string[]>([])
    const [currentCursor, setCurrentCursor] = useState<string | undefined>(
        undefined,
    )

    const goToNextPage = useCallback((nextCursor: string) => {
        setCursorStack((prev) => [...prev, ''])
        setCurrentCursor((prev) => {
            // Push the current cursor onto the stack before moving forward
            setCursorStack((stack) => {
                const newStack = [...stack]
                newStack[newStack.length - 1] = prev ?? ''
                return newStack
            })
            return nextCursor
        })
    }, [])

    const goToPreviousPage = useCallback(() => {
        setCursorStack((prev) => {
            const newStack = [...prev]
            const previousCursor = newStack.pop()
            setCurrentCursor(previousCursor || undefined)
            return newStack
        })
    }, [])

    const resetPagination = useCallback(() => {
        setCursorStack([])
        setCurrentCursor(undefined)
    }, [])

    const canGoPrevious = cursorStack.length > 0

    return {
        currentCursor,
        cursorStack,
        pageSize,
        goToNextPage,
        goToPreviousPage,
        resetPagination,
        canGoPrevious,
    }
}
