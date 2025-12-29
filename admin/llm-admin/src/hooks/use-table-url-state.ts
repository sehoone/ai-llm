'use client'

import { useMemo, useState, useCallback } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import type {
  ColumnFiltersState,
  OnChangeFn,
  PaginationState,
} from '@tanstack/react-table'

type SearchRecord = Record<string, unknown>

type UseTableUrlStateParams = {
  pagination?: {
    pageKey?: string
    pageSizeKey?: string
    defaultPage?: number
    defaultPageSize?: number
  }
  globalFilter?: {
    enabled?: boolean
    key?: string
    trim?: boolean
  }
  columnFilters?: Array<
    | {
        columnId: string
        searchKey: string
        type?: 'string'
        serialize?: (value: unknown) => unknown
        deserialize?: (value: unknown) => unknown
      }
    | {
        columnId: string
        searchKey: string
        type: 'array'
        serialize?: (value: unknown) => unknown
        deserialize?: (value: unknown) => unknown
      }
  >
}

type UseTableUrlStateReturn = {
  globalFilter?: string
  onGlobalFilterChange?: OnChangeFn<string>
  columnFilters: ColumnFiltersState
  onColumnFiltersChange: OnChangeFn<ColumnFiltersState>
  pagination: PaginationState
  onPaginationChange: OnChangeFn<PaginationState>
  ensurePageInRange: (
    pageCount: number,
    opts?: { resetTo?: 'first' | 'last' }
  ) => void
}

export function useTableUrlState(
  params: UseTableUrlStateParams
): UseTableUrlStateReturn {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  const {
    pagination: paginationCfg,
    globalFilter: globalFilterCfg,
    columnFilters: columnFiltersCfg = [],
  } = params

  const pageKey = paginationCfg?.pageKey ?? 'page'
  const pageSizeKey = paginationCfg?.pageSizeKey ?? 'pageSize'
  const defaultPage = paginationCfg?.defaultPage ?? 1
  const defaultPageSize = paginationCfg?.defaultPageSize ?? 10

  const globalFilterKey = globalFilterCfg?.key ?? 'filter'
  const globalFilterEnabled = globalFilterCfg?.enabled ?? true
  const trimGlobal = globalFilterCfg?.trim ?? true

  // Parse search params into a record
  const search = useMemo(() => {
    const obj: SearchRecord = {}
    // We need to iterate over keys to handle arrays correctly
    const keys = Array.from(searchParams.keys())
    const uniqueKeys = new Set(keys)
    
    uniqueKeys.forEach((key) => {
        const values = searchParams.getAll(key)
        if (values.length > 1) {
            obj[key] = values
        } else if (values.length === 1) {
            const value = values[0]
            // Try to parse number
            const num = Number(value)
            if (!isNaN(num) && value.trim() !== '') {
                obj[key] = num
            } else {
                obj[key] = value
            }
        }
    })
    return obj
  }, [searchParams.toString()])

  const updateUrl = useCallback((updater: (prev: SearchRecord) => SearchRecord, replace = false) => {
      const newSearch = updater(search)
      const params = new URLSearchParams()
      
      Object.entries(newSearch).forEach(([key, value]) => {
          if (value === undefined || value === null) return
          if (Array.isArray(value)) {
             value.forEach(v => params.append(key, String(v)))
          } else {
             params.set(key, String(value))
          }
      })
      
      // Sort params to ensure consistent order for comparison
      params.sort()
      
      const queryString = params.toString()
      const url = `${pathname}${queryString ? `?${queryString}` : ''}`

      // Check if URL actually changed by comparing sorted query strings
      const currentParams = new URLSearchParams(searchParams.toString())
      currentParams.sort()
      
      if (params.toString() !== currentParams.toString()) {
        if (replace) {
            router.replace(url)
        } else {
            router.push(url)
        }
      }
  }, [search, pathname, router, searchParams])

  // Build initial column filters from the current search params
  const initialColumnFilters: ColumnFiltersState = useMemo(() => {
    const collected: ColumnFiltersState = []
    for (const cfg of columnFiltersCfg) {
      const raw = (search as SearchRecord)[cfg.searchKey]
      const deserialize = cfg.deserialize ?? ((v: unknown) => v)
      if (cfg.type === 'string') {
        const value = (deserialize(raw) as string) ?? ''
        if (typeof value === 'string' && value.trim() !== '') {
          collected.push({ id: cfg.columnId, value })
        }
      } else {
        // default to array type
        // If raw is a single value but we expect array, wrap it
        let valueToDeserialize = raw
        if (raw !== undefined && !Array.isArray(raw)) {
            valueToDeserialize = [raw]
        }
        
        const value = (deserialize(valueToDeserialize) as unknown[]) ?? []
        if (Array.isArray(value) && value.length > 0) {
          collected.push({ id: cfg.columnId, value })
        }
      }
    }
    return collected
  }, [columnFiltersCfg, search])

  const [columnFilters, setColumnFilters] =
    useState<ColumnFiltersState>(initialColumnFilters)

  const pagination: PaginationState = useMemo(() => {
    const rawPage = (search as SearchRecord)[pageKey]
    const rawPageSize = (search as SearchRecord)[pageSizeKey]
    
    let pageNum = defaultPage
    if (typeof rawPage === 'number') {
        pageNum = rawPage
    } else if (typeof rawPage === 'string') {
        const parsed = Number(rawPage)
        if (!isNaN(parsed)) pageNum = parsed
    }

    let pageSizeNum = defaultPageSize
    if (typeof rawPageSize === 'number') {
        pageSizeNum = rawPageSize
    } else if (typeof rawPageSize === 'string') {
        const parsed = Number(rawPageSize)
        if (!isNaN(parsed)) pageSizeNum = parsed
    }
    
    return { pageIndex: Math.max(0, pageNum - 1), pageSize: pageSizeNum }
  }, [search, pageKey, pageSizeKey, defaultPage, defaultPageSize])

  const onPaginationChange: OnChangeFn<PaginationState> = useCallback((updater) => {
    const next = typeof updater === 'function' ? updater(pagination) : updater
    const nextPage = next.pageIndex + 1
    const nextPageSize = next.pageSize
    
    updateUrl(
      (prev) => ({
        ...prev,
        [pageKey]: nextPage <= defaultPage ? undefined : nextPage,
        [pageSizeKey]:
          nextPageSize === defaultPageSize ? undefined : nextPageSize,
      })
    )
  }, [pagination, pageKey, pageSizeKey, defaultPage, defaultPageSize, updateUrl])

  const [globalFilter, setGlobalFilter] = useState<string | undefined>(() => {
    if (!globalFilterEnabled) return undefined
    const raw = (search as SearchRecord)[globalFilterKey]
    return typeof raw === 'string' ? raw : ''
  })

  const onGlobalFilterChange: OnChangeFn<string> | undefined = useMemo(() =>
    globalFilterEnabled
      ? (updater) => {
          const next =
            typeof updater === 'function'
              ? updater(globalFilter ?? '')
              : updater
          const value = trimGlobal ? next.trim() : next
          setGlobalFilter(value)
          updateUrl(
            (prev) => ({
              ...prev,
              [pageKey]: undefined,
              [globalFilterKey]: value ? value : undefined,
            })
          )
        }
      : undefined, [globalFilterEnabled, globalFilter, trimGlobal, updateUrl, pageKey, globalFilterKey])

  const onColumnFiltersChange: OnChangeFn<ColumnFiltersState> = useCallback((updater) => {
    const next =
      typeof updater === 'function' ? updater(columnFilters) : updater
    setColumnFilters(next)

    const patch: Record<string, unknown> = {}

    for (const cfg of columnFiltersCfg) {
      const found = next.find((f) => f.id === cfg.columnId)
      const serialize = cfg.serialize ?? ((v: unknown) => v)
      if (cfg.type === 'string') {
        const value =
          typeof found?.value === 'string' ? (found.value as string) : ''
        patch[cfg.searchKey] =
          value.trim() !== '' ? serialize(value) : undefined
      } else {
        const value = Array.isArray(found?.value)
          ? (found!.value as unknown[])
          : []
        patch[cfg.searchKey] = value.length > 0 ? serialize(value) : undefined
      }
    }

    updateUrl(
      (prev) => ({
        ...prev,
        [pageKey]: undefined,
        ...patch,
      })
    )
  }, [columnFilters, columnFiltersCfg, updateUrl, pageKey])

  const ensurePageInRange = useCallback((
    pageCount: number,
    opts: { resetTo?: 'first' | 'last' } = { resetTo: 'first' }
  ) => {
    const currentPage = (search as SearchRecord)[pageKey]
    const pageNum = typeof currentPage === 'number' ? currentPage : defaultPage
    if (pageCount > 0 && pageNum > pageCount) {
      updateUrl(
        (prev) => ({
          ...prev,
          [pageKey]: opts.resetTo === 'last' ? pageCount : undefined,
        }),
        true // replace
      )
    }
  }, [search, pageKey, defaultPage, updateUrl])

  return {
    globalFilter: globalFilterEnabled ? (globalFilter ?? '') : undefined,
    onGlobalFilterChange,
    columnFilters,
    onColumnFiltersChange,
    pagination,
    onPaginationChange,
    ensurePageInRange,
  }
}
