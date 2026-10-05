import { describe, expect, it } from 'vitest';
import {
	EMPTY,
	NEW_VISIT_GAP_MS,
	SNOOZE_MS,
	chromeIntentUrl,
	noteVisit,
	platformFor,
	shouldOffer,
	snooze
} from './installPrompt';

const ANDROID_CHROME =
	'Mozilla/5.0 (Linux; Android 13; SM-A135F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36';
const IPHONE_SAFARI =
	'Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1';
const IPHONE_CHROME =
	'Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/129.0 Mobile/15E148 Safari/604.1';
const FACEBOOK_ANDROID =
	'Mozilla/5.0 (Linux; Android 13; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/480.0]';

describe('platformFor', () => {
	it('uses the native dialog when the browser offers one', () => {
		expect(platformFor(ANDROID_CHROME, true)).toBe('native');
	});
	it('explains Share → Add to Home Screen on iPhone Safari only', () => {
		expect(platformFor(IPHONE_SAFARI, false)).toBe('ios');
		expect(platformFor(IPHONE_CHROME, false)).toBe('none');
	});
	it('sends in-app browsers to the real browser', () => {
		expect(platformFor(FACEBOOK_ANDROID, false)).toBe('inapp');
	});
	it('offers nothing where installing isn’t possible', () => {
		expect(platformFor(ANDROID_CHROME, false)).toBe('none');
	});
});

describe('shouldOffer', () => {
	const now = 10 * SNOOZE_MS;
	it('waits for a second visit', () => {
		let s = noteVisit(EMPTY, now);
		expect(shouldOffer(s, 'native', false, now)).toBe(false);
		s = noteVisit(s, now + 60_000); // same visit
		expect(s.visits).toBe(1);
		s = noteVisit(s, now + NEW_VISIT_GAP_MS + 60_000);
		expect(shouldOffer(s, 'native', false, now)).toBe(true);
	});
	it('never once installed or running as the app', () => {
		const s = { ...EMPTY, visits: 5 };
		expect(shouldOffer(s, 'native', true, now)).toBe(false);
		expect(shouldOffer({ ...s, installed: true }, 'native', false, now)).toBe(false);
	});
	it('stays away for 30 days after "Not now"', () => {
		const s = snooze({ ...EMPTY, visits: 5 }, now);
		expect(shouldOffer(s, 'ios', false, now + SNOOZE_MS - 1)).toBe(false);
		expect(shouldOffer(s, 'ios', false, now + SNOOZE_MS)).toBe(true);
	});
});

describe('chromeIntentUrl', () => {
	it('reopens the same page in Chrome', () => {
		expect(chromeIntentUrl('https://ochorus.com/sw/books/x/2/?plan=p&day=2')).toBe(
			'intent://ochorus.com/sw/books/x/2/?plan=p&day=2#Intent;scheme=https;package=com.android.chrome;end'
		);
	});
});
