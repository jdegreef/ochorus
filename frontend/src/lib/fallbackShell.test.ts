import { describe, expect, it } from 'vitest';
import { FALLBACK_PATH, FALLBACK_ROBOTS, markFallbackNoindex } from './fallbackShell';

const shell = '<html><head><title>x</title></head><body></body></html>';

describe('markFallbackNoindex', () => {
	it('marks the SPA fallback shell noindex in its raw HTML', () => {
		const out = markFallbackNoindex(shell, FALLBACK_PATH);
		expect(out).toContain(FALLBACK_ROBOTS);
		expect(out.indexOf(FALLBACK_ROBOTS)).toBeLessThan(out.indexOf('</head>'));
	});

	it('leaves every prerendered page alone', () => {
		for (const p of ['/', '/books/', '/books/x/', '/es/books/x/1/']) {
			expect(markFallbackNoindex(shell, p)).toBe(shell);
		}
	});

	it('is a no-op on a chunk without the head close', () => {
		expect(markFallbackNoindex('<body></body>', FALLBACK_PATH)).toBe('<body></body>');
	});
});
