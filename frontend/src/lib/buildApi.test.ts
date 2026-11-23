import { describe, expect, it } from 'vitest';
import {
	buildApiBase,
	DEFAULT_LOCAL_API_PORT,
	localBuildApiOrigin,
	retarget,
	SERVICE_KEY_HEADER,
	serviceKeyHeaders,
	withServiceKey
} from './buildApi';

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

describe('serviceKeyHeaders', () => {
	it('is empty without a key, so an unconfigured build is unchanged', () => {
		expect(serviceKeyHeaders({})).toEqual({});
		expect(serviceKeyHeaders({ OCHORUS_API_KEY: '  ' })).toEqual({});
	});
	it('names the key the API guard reads', () => {
		expect(serviceKeyHeaders({ OCHORUS_API_KEY: ' s3cret ' })).toEqual({
			[SERVICE_KEY_HEADER]: 's3cret'
		});
	});
});

describe('withServiceKey', () => {
	const API = 'https://api.ochorus.com';
	const KEY = { [SERVICE_KEY_HEADER]: 's3cret' };

	it('adds the key to a request for the API, keeping its own headers', () => {
		const [out, init] = withServiceKey(
			`${API}/api/library/books/`,
			{ headers: { accept: 'x' } },
			API,
			KEY
		);
		expect(out).toBeInstanceOf(Request);
		expect(init).toBeUndefined();
		const req = out as Request;
		expect(req.headers.get(SERVICE_KEY_HEADER)).toBe('s3cret');
		expect(req.headers.get('accept')).toBe('x');
		expect(req.url).toBe(`${API}/api/library/books/`);
	});

	it('never sends the key anywhere else', () => {
		const init = {};
		for (const url of [
			'https://example.com/api/x',
			'/api/library/books/',
			'https://api.ochorus.com.evil.example/'
		]) {
			const [out, outInit] = withServiceKey(url, init, API, KEY);
			expect(out).toBe(url);
			expect(outInit).toBe(init);
		}
	});

	it('leaves the request alone when no key is configured', () => {
		const req = new Request(`${API}/api/library/books/`);
		expect(withServiceKey(req, undefined, API, {})[0]).toBe(req);
	});
});
