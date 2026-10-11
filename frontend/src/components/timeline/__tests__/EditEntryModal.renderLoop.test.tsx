import { describe, it, expect, vi, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EditEntryModal } from '../EditEntryModal'

// Regression test for #101: TimelinePage always mounts EditEntryModal. While it
// is closed (`entry` is null) the entry-assets query is disabled, so its `data`
// is undefined and `const { data: linkedAssets = [] }` produced a new array on
// every render. The effect keyed on `linkedAssets` then set state on every
// render, which rendered again - "Maximum update depth exceeded".

// Each render calls useEntryAssets once. Throwing past a generous limit turns
// the infinite loop into a normal test failure instead of a hung worker.
const MAX_RENDERS = 50
let renders = 0

vi.mock('@/hooks/useTimeline', () => ({
  useUpdateTimelineEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))
vi.mock('@/hooks/useAssets', () => ({
  // A disabled query: data stays undefined on every render.
  useAssets: () => ({ data: undefined }),
  useEntryAssets: () => {
    renders += 1
    if (renders > MAX_RENDERS) throw new Error(`EditEntryModal rendered more than ${MAX_RENDERS} times`)
    return { data: undefined }
  },
  useLinkAssetsToEntry: () => ({ mutateAsync: vi.fn() }),
  useUnlinkAssetFromEntry: () => ({ mutateAsync: vi.fn() }),
}))
vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector: (s: { addToast: () => void }) => unknown) =>
    selector({ addToast: vi.fn() }),
}))

describe('EditEntryModal while closed', () => {
  afterEach(() => vi.restoreAllMocks())

  it('does not re-render in a loop when no entry is open', () => {
    renders = 0
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <QueryClientProvider client={new QueryClient()}>
        <EditEntryModal entry={null} incidentId="incident-1" onClose={() => {}} />
      </QueryClientProvider>
    )

    const loopWarnings = consoleError.mock.calls.filter((args) =>
      String(args[0]).includes('Maximum update depth')
    )
    expect(loopWarnings).toHaveLength(0)
    expect(renders).toBeLessThan(5)
  })
})
