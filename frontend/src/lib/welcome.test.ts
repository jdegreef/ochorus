import { beforeEach, describe, expect, it } from 'vitest';
import { welcome } from './welcome.svelte';

beforeEach(() => {
	localStorage.clear();
	welcome.pending = false;
	welcome.pagePending = false;
	welcome.inProgress = false;
});

describe('sign-up welcome', () => {
	it('is offered to a new account and survives a reload', () => {
		welcome.offer();
		expect(welcome.pending).toBe(true);
		welcome.pending = false;
		welcome.init();
		expect(welcome.pending).toBe(true);
	});

	it('never comes back once answered', () => {
		welcome.offer();
		welcome.done();
		expect(welcome.pending).toBe(false);
		welcome.offer();
		welcome.init();
		expect(welcome.pending).toBe(false);
	});

	it('is not pending on a device that was never offered it', () => {
		welcome.init();
		expect(welcome.pending).toBe(false);
	});

	it('sends a new account to the welcome page once, apart from the palette', () => {
		welcome.offer();
		expect(welcome.pagePending).toBe(true);
		welcome.pageSeen();
		welcome.init();
		expect(welcome.pagePending).toBe(false);
		// The palette card is still owed: seeing the page does not answer it.
		expect(welcome.pending).toBe(true);
		welcome.offer();
		expect(welcome.pagePending).toBe(false);
	});

	it('keeps the page owed when only the palette was answered', () => {
		welcome.offer();
		welcome.done();
		welcome.pagePending = false;
		welcome.init();
		expect(welcome.pagePending).toBe(true);
	});

	it('forgets the page on sign-out so the next account is not sent there', () => {
		welcome.offer();
		welcome.forgetPage();
		expect(welcome.pagePending).toBe(false);
		welcome.init();
		expect(welcome.pagePending).toBe(false);
		// The palette card is a device preference and survives.
		expect(welcome.pending).toBe(true);
	});

	it('tracks the checklist after the page is seen, until it is finished', () => {
		welcome.offer();
		expect(welcome.inProgress).toBe(false);
		welcome.pageSeen();
		expect(welcome.inProgress).toBe(true);
		welcome.inProgress = false;
		welcome.init();
		expect(welcome.inProgress).toBe(true);

		welcome.finishProgress();
		welcome.init();
		expect(welcome.inProgress).toBe(false);
		// Finished stays finished: no new redirect, no card on a later visit.
		welcome.offer();
		welcome.pageSeen();
		expect(welcome.pagePending).toBe(false);
		expect(welcome.inProgress).toBe(false);
	});

	it('never shows the card to a reader who did not come through the welcome', () => {
		welcome.init();
		expect(welcome.inProgress).toBe(false);
	});

	it('drops the card with the rest of the welcome on sign-out', () => {
		welcome.offer();
		welcome.pageSeen();
		welcome.forgetPage();
		welcome.init();
		expect(welcome.inProgress).toBe(false);
	});
});
