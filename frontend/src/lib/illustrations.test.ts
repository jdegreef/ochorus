import { describe, expect, it } from 'vitest';
import { illustrationSrcs } from './illustrations';

describe('illustrationSrcs', () => {
	it('lists each self-hosted illustration once, in order', () => {
		const body =
			'<p>a</p><figure><img alt="x" src="/illustrations/b/one.jpg" width="1"/>' +
			'<figcaption>c</figcaption></figure><p>d</p>' +
			'<figure><img alt="y" src="/illustrations/b/two.webp"/></figure>' +
			'<figure><img src="/illustrations/b/one.jpg" alt="again"/></figure>';
		expect(illustrationSrcs(body)).toEqual(['/illustrations/b/one.jpg', '/illustrations/b/two.webp']);
	});

	it('finds nothing in a body without pictures, or pointing elsewhere', () => {
		expect(illustrationSrcs('<p>Only words.</p>')).toEqual([]);
		expect(illustrationSrcs('<img alt="x" src="/covers/a.png"/>')).toEqual([]);
	});
});
