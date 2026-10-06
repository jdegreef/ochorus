import { flushSync, mount, unmount } from 'svelte';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The sign-up panel's form: an email and a password, no emailed code.
 */
const auth = vi.hoisted(() => ({
	enabled: true,
	initialized: true,
	user: null,
	signUp: vi.fn(),
	resendSignup: vi.fn(),
	signInWithGoogle: vi.fn()
}));
vi.mock('$lib/auth.svelte', () => ({ auth }));
const signupStarted = vi.hoisted(() => vi.fn());
vi.mock('$lib/signupSource', () => ({ signupStarted }));

const { default: SignUpForm } = await import('./SignUpForm.svelte');

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
const tick = () => new Promise((r) => setTimeout(r, 0));

function type(input: HTMLInputElement, value: string) {
	input.value = value;
	input.dispatchEvent(new Event('input', { bubbles: true }));
	flushSync();
}
const submit = (form: HTMLFormElement) =>
	form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));

function fillAndSubmit() {
	type(target.querySelector('input[type=email]')!, 'grace@example.org');
	type(target.querySelector('input[autocomplete=new-password]')!, 'amazing grace');
	submit(target.querySelector('form')!);
}

// jsdom has no layout: the password field measures its Show/Hide label.
beforeAll(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			unobserve() {}
			disconnect() {}
		}
	);
});
afterAll(() => {
	vi.unstubAllGlobals();
});

beforeEach(() => {
	auth.signUp.mockReset().mockResolvedValue(null);
	auth.resendSignup.mockReset().mockResolvedValue(null);
	signupStarted.mockReset();
	target = document.body.appendChild(document.createElement('div'));
	component = mount(SignUpForm, { target, props: { returnTo: 'https://ochorus.test/books/humility' } });
	flushSync();
});
afterEach(() => {
	if (component) unmount(component);
	target.remove();
});

describe('SignUpForm', () => {
	it('asks for a password, not a code', () => {
		expect(target.querySelector('input[autocomplete=new-password]')).not.toBeNull();
		expect(target.querySelector('input[autocomplete=one-time-code]')).toBeNull();
	});

	it('creates the account with the email and password, returning to this page', async () => {
		fillAndSubmit();
		await tick();
		flushSync();
		expect(auth.signUp).toHaveBeenCalledWith(
			'grace@example.org',
			'amazing grace',
			'https://ochorus.test/books/humility'
		);
		// No session yet (email confirmation): say where the link went.
		expect(target.querySelector('form')).toBeNull();
		expect(target.querySelector('[role=status]')).not.toBeNull();
	});

	it('keeps the form and shows the error when sign-up fails', async () => {
		auth.signUp.mockResolvedValue('weak_password');
		fillAndSubmit();
		await tick();
		flushSync();
		expect(target.querySelector('form')).not.toBeNull();
		expect(target.querySelector('[role=alert]')?.textContent).not.toBe('');
	});

	it('counts one sign-up start however many times the reader retries', async () => {
		auth.signUp.mockResolvedValue('weak_password');
		fillAndSubmit();
		await tick();
		submit(target.querySelector('form')!);
		await tick();
		expect(auth.signUp).toHaveBeenCalledTimes(2);
		expect(signupStarted).toHaveBeenCalledTimes(1);
	});

	it('re-sends the confirmation email, not a magic link', async () => {
		fillAndSubmit();
		await tick();
		flushSync();
		target.querySelector<HTMLButtonElement>('.suf button')!.click();
		await tick();
		flushSync();
		expect(auth.resendSignup).toHaveBeenCalledWith(
			'grace@example.org',
			'https://ochorus.test/books/humility'
		);
		expect(target.querySelector('[role=status]')?.textContent).not.toBe('');
	});
});
