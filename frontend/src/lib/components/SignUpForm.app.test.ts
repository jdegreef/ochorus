import { flushSync, mount, unmount } from 'svelte';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The sign-up panel's form in the phone app (`auth.emailCodes`, no Google): the
 * confirmation is a code typed in here, since the email's link cannot come back
 * to the app. SignUpForm.test.ts covers the website's.
 */
const auth = vi.hoisted(() => ({
	enabled: true,
	googleEnabled: false,
	emailCodes: true,
	initialized: true,
	user: null as { email: string } | null,
	signUp: vi.fn(),
	resendSignup: vi.fn(),
	signInWithGoogle: vi.fn(),
	verifyEmailCode: vi.fn()
}));
vi.mock('$lib/auth.svelte', () => ({ auth }));
vi.mock('$lib/signupSource', () => ({ signupStarted: vi.fn() }));

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
	auth.user = null;
	auth.signUp.mockReset().mockResolvedValue(null);
	auth.verifyEmailCode.mockReset().mockResolvedValue(null);
	target = document.body.appendChild(document.createElement('div'));
	component = mount(SignUpForm, { target, props: { returnTo: 'capacitor://localhost/books/humility' } });
	flushSync();
});
afterEach(() => {
	if (component) unmount(component);
	target.remove();
});

async function signUp() {
	type(target.querySelector('input[type=email]')!, 'grace@example.org');
	type(target.querySelector('input[autocomplete=new-password]')!, 'amazing grace');
	submit(target.querySelector('form')!);
	await tick();
	flushSync();
}

describe('SignUpForm in the app', () => {
	it('offers no Google sign-in', () => {
		expect(target.querySelector('.google-btn')).toBeNull();
		expect(target.querySelector('input[autocomplete=new-password]')).not.toBeNull();
	});

	it('confirms the new account with the emailed code', async () => {
		await signUp();
		const code = target.querySelector<HTMLInputElement>('input[autocomplete=one-time-code]');
		expect(code).not.toBeNull();
		type(code!, '123456');
		submit(code!.form!);
		await tick();
		expect(auth.verifyEmailCode).toHaveBeenCalledWith('grace@example.org', '123456', 'signup');
	});

	it('shows a wrong code’s error and keeps the field', async () => {
		auth.verifyEmailCode.mockResolvedValue('otp_expired');
		await signUp();
		const code = target.querySelector<HTMLInputElement>('input[autocomplete=one-time-code]')!;
		type(code, '000000');
		submit(code.form!);
		await tick();
		flushSync();
		expect(target.querySelector('input[autocomplete=one-time-code]')).not.toBeNull();
		expect(code.form!.querySelector('[role=alert]')?.textContent).not.toBe('');
	});
});
