import { describe, expect, it } from 'vitest';
import { listenBookFor, requestBookListen, takeBookListen } from './listenBook';

describe('listen to the whole book', () => {
	it('is offered on a book of the Bible only', () => {
		expect(listenBookFor({ series: { slug: 'the-bible' } })).toBe(true);
		expect(listenBookFor({ series: { slug: 'anchored' } })).toBe(false);
		expect(listenBookFor({ series: null })).toBe(false);
		expect(listenBookFor({})).toBe(false);
	});

	it('starts listening on the chapter asked for, once', () => {
		requestBookListen('psalms', 1);
		expect(takeBookListen('psalms', 1)).toBe(true);
		expect(takeBookListen('psalms', 1)).toBe(false);
	});

	it('is dropped by the first chapter arrival, matching or not', () => {
		requestBookListen('psalms', 1);
		expect(takeBookListen('genesis', 1)).toBe(false);
		expect(takeBookListen('psalms', 1)).toBe(false);
	});
});
