import { FaChevronLeft, FaChevronRight } from 'react-icons/fa6'
import { pageWindow } from '@/lib/pagination'

interface PaginationProps {
  page: number
  perPage: number
  total: number
  pageSizes?: readonly number[]
  onPageChange: (page: number) => void
  onPerPageChange?: (perPage: number) => void
}

// Pagination bar for server-paged lists (#127): "Showing 26 to 50 of 132",
// page size, previous/next and page numbers.
export function Pagination({ page, perPage, total, pageSizes, onPageChange, onPerPageChange }: PaginationProps) {
  const lastPage = Math.max(1, Math.ceil(total / perPage))
  const from = total === 0 ? 0 : (page - 1) * perPage + 1
  const to = Math.min(page * perPage, total)

  return (
    <nav
      aria-label="Pagination"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        flexWrap: 'wrap',
        fontSize: 12,
        color: 'var(--text-muted)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span aria-live="polite">
          Showing {from} to {to} of {total}
        </span>
        {pageSizes && onPerPageChange && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            Per page
            <select
              className="form-input"
              value={perPage}
              onChange={(e) => onPerPageChange(Number(e.target.value))}
              style={{ width: 'auto', padding: '2px 8px', fontSize: 12 }}
            >
              {pageSizes.map((size) => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {lastPage > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <FaChevronLeft size={10} aria-hidden="true" />
          </button>
          {pageWindow(page, lastPage).map((p, i) =>
            p === 'gap' ? (
              <span key={`gap-${i}`} aria-hidden="true" style={{ padding: '0 4px' }}>…</span>
            ) : (
              <button
                key={p}
                type="button"
                className={`btn btn-sm ${p === page ? 'btn-accent' : 'btn-ghost'}`}
                onClick={() => onPageChange(p)}
                aria-current={p === page ? 'page' : undefined}
                aria-label={`Page ${p}`}
                style={{ minWidth: 32, justifyContent: 'center' }}
              >
                {p}
              </button>
            ),
          )}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= lastPage}
            aria-label="Next page"
          >
            <FaChevronRight size={10} aria-hidden="true" />
          </button>
        </div>
      )}
    </nav>
  )
}
