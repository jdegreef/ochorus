import { describe, expect, it } from 'vitest';
import { ALLOWED, evaluate } from '../../scripts/audit-runtime.mjs';

const advisory = (name: string, ghsa: string, severity: string) => ({
	source: 1,
	name,
	severity,
	title: `${name} advisory`,
	url: `https://github.com/advisories/${ghsa}`
});

const ids = (list: { id: string }[]) => list.map((a) => a.id);

describe('audit-runtime allowlist (scripts/audit-runtime.mjs)', () => {
	it('lets an allowed high advisory through and blocks an unknown one', () => {
		const report = {
			vulnerabilities: {
				picomatch: { via: [advisory('picomatch', 'GHSA-fc5q-39xc-vjpf', 'high')] },
				vite: { via: ['picomatch'] },
				evil: { via: [advisory('evil', 'GHSA-aaaa-bbbb-cccc', 'critical')] }
			}
		};
		const { blocking, allowed } = evaluate(report, {
			'GHSA-fc5q-39xc-vjpf': ALLOWED['GHSA-fc5q-39xc-vjpf']
		});
		expect(ids(allowed)).toEqual(['GHSA-fc5q-39xc-vjpf']);
		expect(ids(blocking)).toEqual(['GHSA-aaaa-bbbb-cccc']);
	});

	it('ignores advisories below high', () => {
		const report = {
			vulnerabilities: { cookie: { via: [advisory('cookie', 'GHSA-pxg6-pf52-xh8x', 'low')] } }
		};
		expect(evaluate(report, {}).blocking).toEqual([]);
	});

	it('reports an allowed advisory that npm no longer flags as stale', () => {
		expect(evaluate({ vulnerabilities: {} }).stale.sort()).toEqual(Object.keys(ALLOWED).sort());
	});

	it('gives every entry a package, a reason and a way to retire it', () => {
		for (const [id, entry] of Object.entries(ALLOWED)) {
			expect(id).toMatch(/^GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}$/);
			expect(entry.package).toBeTruthy();
			expect(entry.reason.length).toBeGreaterThan(40);
			expect(entry.retire.length).toBeGreaterThan(20);
		}
	});
});
