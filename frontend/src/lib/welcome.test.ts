import { beforeEach, describe, expect, it } from 'vitest';
import { welcome } from './welcome.svelte';

beforeEach(() => {
	localStorage.clear();
	welcome.pending = false;
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
});
