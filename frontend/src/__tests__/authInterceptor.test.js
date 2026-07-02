/**
 * #223: every request to the per-user backends carries the signed-in user's
 * Firebase ID token; public KB reads get none; token failures never block.
 */
import { describe, it, expect, vi } from 'vitest';

vi.mock('../firebase', () => ({ auth: {} }));

import { attachAuthTokenInterceptor } from '../services/api';

// The vitest setup stubs the VITE_* base URLs — use the same source of
// truth the interceptor reads.
const PM_BASE = 'http://test-profile-manager.example';
const COUNSELOR_BASE = 'http://test-counselor.example';
const KB_BASE = 'http://test-kb.example';

function capture(getAuthInstance) {
  let handler;
  const axiosLike = { interceptors: { request: { use: (fn) => { handler = fn; } } } };
  attachAuthTokenInterceptor(axiosLike, getAuthInstance);
  return handler;
}

const signedIn = () => ({ currentUser: { getIdToken: async () => 'fb-token' } });

describe('auth token interceptor', () => {
  it('attaches the Firebase ID token to profile-manager calls', async () => {
    const handler = capture(signedIn);
    const cfg = await handler({ url: `${PM_BASE}/get-profile`, headers: {} });
    expect(cfg.headers.Authorization).toBe('Bearer fb-token');
  });

  it('attaches to counselor-agent calls', async () => {
    const handler = capture(signedIn);
    const cfg = await handler({ url: `${COUNSELOR_BASE}/work-feed`, headers: {} });
    expect(cfg.headers.Authorization).toBe('Bearer fb-token');
  });

  it('leaves public KB reads untouched', async () => {
    const handler = capture(signedIn);
    const cfg = await handler({ url: `${KB_BASE}?id=duke`, headers: {} });
    expect(cfg.headers.Authorization).toBeUndefined();
  });

  it('does not leak the token to a look-alike host', async () => {
    const handler = capture(signedIn);
    const cfg = await handler({ url: `${PM_BASE}.evil.com/steal`, headers: {} });
    expect(cfg.headers.Authorization).toBeUndefined();
  });

  it('signed-out users send no token (backend AUTH_MODE decides)', async () => {
    const handler = capture(() => ({ currentUser: null }));
    const cfg = await handler({ url: `${PM_BASE}/get-profile`, headers: {} });
    expect(cfg.headers.Authorization).toBeUndefined();
  });

  it('a token failure never blocks the request', async () => {
    const handler = capture(() => ({
      currentUser: { getIdToken: async () => { throw new Error('refresh failed'); } },
    }));
    const cfg = await handler({ url: `${PM_BASE}/get-profile`, headers: {} });
    expect(cfg).toBeTruthy();
    expect(cfg.headers.Authorization).toBeUndefined();
  });
});
