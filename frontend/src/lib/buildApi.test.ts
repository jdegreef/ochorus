import { describe, expect, it } from 'vitest';
import { buildApiBase, DEFAULT_LOCAL_API_PORT, localBuildApiOrigin, retarget } from './buildApi';

const PROD = 'https://api.ochorus.com';
const LOCAL = 'http://127.0.0.1:8765';

describe('localBuildApiOrigin', () => {
	it('is inert unless the flag says local', () => {
		expect(localBuildApiOrigin({})).toBeNull();
		expect(localBuildApiOrigin({ OCHORUS_BUILD_API: '' })).toBeNull();
		expect(localBuildApiOrigin({ OCHORUS_BUILD_API: 'prod' })).toBeNull();
		expect(localBuildApiOrigin({ OCHORUS_BUILD_API_PORT: '9000' })).toBeNull();
	});

	it('names the loopback port, default or given', () => {
		expect(localBuildApiOrigin({ OCHORUS_BUILD_API: 'local' })).toBe(
			`http://127.0.0.1:${DEFAULT_LOCAL_API_PORT}`
		);
		expect(
			localBuildApiOrigin({ OCHORUS_BUILD_API: ' LOCAL ', OCHORUS_BUILD_API_PORT: '9001' })
		).toBe('http://127.0.0.1:9001');
	});

	it('refuses a port that is not one', () => {
		expect(() =>
			localBuildApiOrigin({ OCHORUS_BUILD_API: 'local', OCHORUS_BUILD_API_PORT: 'x' })
		).toThrow();
		expect(() =>
			localBuildApiOrigin({ OCHORUS_BUILD_API: 'local', OCHORUS_BUILD_API_PORT: '70000' })
		).toThrow();
	});
});

describe('buildApiBase', () => {
	it('is PUBLIC_API_BASE_URL without the flag — today’s behaviour', () => {
		expect(buildApiBase({ PUBLIC_API_BASE_URL: `${PROD}/` })).toBe(PROD);
		expect(buildApiBase({})).toBe('');
	});

	it('is the local API with it, whatever PUBLIC_API_BASE_URL says', () => {
		expect(buildApiBase({ OCHORUS_BUILD_API: 'local', PUBLIC_API_BASE_URL: PROD })).toBe(LOCAL);
	});
});

describe('retarget', () => {
	it('moves a Request for the API to the local origin, keeping path, query and headers', () => {
		const req = new Request(`${PROD}/api/library/books/?language=es`, {
			headers: { accept: 'application/json' }
		});
		const out = retarget(req, PROD, LOCAL);
		expect(out.url).toBe(`${LOCAL}/api/library/books/?language=es`);
		expect(out.method).toBe('GET');
		expect(out.headers.get('accept')).toBe('application/json');
	});

	it('moves a URL string and a URL object the same way', () => {
		expect(retarget(`${PROD}/api/health/`, PROD, LOCAL)).toBe(`${LOCAL}/api/health/`);
		const u = retarget(new URL(`${PROD}/api/x/?a=1`), PROD, LOCAL);
		expect(u).toBeInstanceOf(URL);
		expect(u.href).toBe(`${LOCAL}/api/x/?a=1`);
	});

	it('leaves anything not addressed to the API alone', () => {
		const other = new Request('https://api.takeroot.bible/api/bible/x');
		expect(retarget(other, PROD, LOCAL)).toBe(other);
		expect(retarget('/covers/a.webp', PROD, LOCAL)).toBe('/covers/a.webp');
	});
});
