import { describe, expect, it, vi } from 'vitest';
import { MAX_REPORTS, armCspReports, describeViolation } from './cspReport';

const ORIGIN = 'https://ochorus.com';

/** A document stand-in that records listeners and lets a test fire events. */
function fakeTarget() {
	const listeners = new Set<(e: Event) => void>();
	return {
		addEventListener: (_: string, fn: (e: Event) => void) => listeners.add(fn),
		removeEventListener: (_: string, fn: (e: Event) => void) => listeners.delete(fn),
		fire: (init: Record<string, unknown>) =>
			listeners.forEach((fn) => fn({ disposition: 'enforce', ...init } as unknown as Event)),
		count: () => listeners.size
	};
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe('describeViolation', () => {
	const v = (o: Record<string, string>) =>
		describeViolation({ disposition: 'enforce', ...o } as never, ORIGIN);

	it('reduces a blocked URL to its origin, dropping path and query', () => {
		expect(
			v({ effectiveDirective: 'connect-src', blockedURI: 'https://evil.example/x?token=abc' })
		).toEqual({ directive: 'connect-src', blocked: 'https://evil.example' });
	});

	it('ignores extensions, by blocked URL or by source file', () => {
		expect(v({ effectiveDirective: 'script-src', blockedURI: 'chrome-extension://abc/x.js' })).toBeNull();
		expect(
			v({ effectiveDirective: 'script-src', blockedURI: 'inline', sourceFile: 'moz-extension://x/c.js' })
		).toBeNull();
	});

	it('reports inline code only when it ran from this origin', () => {
		expect(
			v({ effectiveDirective: 'script-src-elem', blockedURI: 'inline', sourceFile: `${ORIGIN}/books/x/` })
		).toEqual({ directive: 'script-src-elem', blocked: 'inline' });
		expect(v({ effectiveDirective: 'script-src', blockedURI: 'inline', sourceFile: '' })).toBeNull();
	});

	it('ignores schemes with nothing to fix, and report-only policies', () => {
		expect(v({ effectiveDirective: 'img-src', blockedURI: 'data' })).toBeNull();
		expect(v({ effectiveDirective: 'img-src', blockedURI: 'blob:https://ochorus.com/1' })).toBeNull();
		expect(
			describeViolation(
				{ disposition: 'report', effectiveDirective: 'img-src', blockedURI: 'https://a.example/' } as never,
				ORIGIN
			)
		).toBeNull();
	});
});

describe('armCspReports', () => {
	it('loads nothing until a violation of ours happens', async () => {
		const t = fakeTarget();
		const load = vi.fn();
		armCspReports({ load, origin: ORIGIN, target: t as never });
		t.fire({ effectiveDirective: 'script-src', blockedURI: 'chrome-extension://abc/x.js' });
		await flush();
		expect(load).not.toHaveBeenCalled();
	});

	it('sends each distinct violation once, tagged, as a warning', async () => {
		const t = fakeTarget();
		const sdk = { captureMessage: vi.fn() };
		armCspReports({ load: () => Promise.resolve(sdk), origin: ORIGIN, target: t as never });
		t.fire({ effectiveDirective: 'connect-src', blockedURI: 'https://x.supabase.co/auth' });
		t.fire({ effectiveDirective: 'connect-src', blockedURI: 'https://x.supabase.co/rest' });
		await flush();
		expect(sdk.captureMessage).toHaveBeenCalledTimes(1);
		expect(sdk.captureMessage).toHaveBeenCalledWith('CSP blocked connect-src: https://x.supabase.co', {
			level: 'warning',
			tags: { csp_directive: 'connect-src', csp_blocked: 'https://x.supabase.co' }
		});
	});

	it(`stops after ${MAX_REPORTS} reports on one page`, async () => {
		const t = fakeTarget();
		const sdk = { captureMessage: vi.fn() };
		armCspReports({ load: () => Promise.resolve(sdk), origin: ORIGIN, target: t as never });
		for (let i = 0; i < MAX_REPORTS + 3; i++) {
			t.fire({ effectiveDirective: 'img-src', blockedURI: `https://h${i}.example/a.png` });
		}
		await flush();
		expect(sdk.captureMessage).toHaveBeenCalledTimes(MAX_REPORTS);
	});

	it('never throws when the SDK fails to load', async () => {
		const t = fakeTarget();
		armCspReports({ load: () => Promise.reject(new Error('offline')), origin: ORIGIN, target: t as never });
		t.fire({ effectiveDirective: 'img-src', blockedURI: 'https://a.example/' });
		await flush();
	});

	it('removes its listener when stopped', () => {
		const t = fakeTarget();
		const stop = armCspReports({ load: vi.fn(), origin: ORIGIN, target: t as never });
		expect(t.count()).toBe(1);
		stop();
		expect(t.count()).toBe(0);
	});
});
