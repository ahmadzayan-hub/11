import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../shared/api'

function mockFetchOnce(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const impl = {
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    ...response,
  } as Response
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(impl))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api client', () => {
  it('returns parsed JSON for successful requests', async () => {
    mockFetchOnce({ json: () => Promise.resolve({ status: 'ok', agent_name: 'A', version: '1' }) })
    const result = await api.health()
    expect(result.status).toBe('ok')
  })

  it('surfaces the server "detail" message on API errors', async () => {
    mockFetchOnce({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: 'This session has ended.' }),
    })
    await expect(api.sendMessage('sid', 'hello')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: 'This session has ended.',
    })
  })

  it('maps network failures to a friendly offline error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    try {
      await api.health()
      expect.unreachable('health() should have thrown')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).offline).toBe(true)
      expect((error as ApiError).message).toMatch(/Cannot reach/)
    }
  })

  it('falls back to a status message when the error body is not JSON', async () => {
    mockFetchOnce({ ok: false, status: 500, json: () => Promise.reject(new Error('not json')) })
    await expect(api.health()).rejects.toMatchObject({ message: 'Request failed (500).' })
  })
})
