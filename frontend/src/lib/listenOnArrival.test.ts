import { describe, expect, it } from 'vitest';
import { LISTEN_PARAM, wantsListen, withoutListen } from './listenOnArrival';

describe('listen on arrival', () => {
	it('reads the request from the link, with or without a value', () => {
		expect(wantsListen(new URL(`https://ochorus.com/sermons/a?${LISTEN_PARAM}`))).toBe(true);
		expect(wantsListen(new URL(`https://ochorus.com/sermons/a?${LISTEN_PARAM}=1`))).toBe(true);
		expect(wantsListen(new URL('https://ochorus.com/sermons/a'))).toBe(false);
	});

	it('drops only the request, keeping the rest of the URL', () => {
		const url = new URL(`https://ochorus.com/es/sermons/a?${LISTEN_PARAM}&x=2#p3`);
		expect(withoutListen(url).href).toBe('https://ochorus.com/es/sermons/a?x=2#p3');
	});
});
