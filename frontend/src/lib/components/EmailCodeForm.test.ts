import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The passwordless form: send an email, then finish with its 6-digit code.
 */
const auth = vi.hoisted(() => ({
	enabled: true,
	initialized: true,
	user: null,
	signInWithMagicLink: vi.fn(),
	verifyEmailCode: vi.fn(),
	signInWithGoogle: vi.fn()
}));
vi.mock('$lib/auth.svelte', () => ({ auth }));

const { default: EmailCodeForm } = await import('./EmailCodeForm.svelte');

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

beforeEach(() => {
	auth.signInWithMagicLink.mockReset().mockResolvedValue(null);
	auth.verifyEmailCode.mockReset().mockResolvedValue(null);
	target = document.body.appendChild(document.createElement('div'));
	component = mount(EmailCodeForm, { target, props: { counts: false } });
	flushSync();
});
afterEach(() => {
	if (component) unmount(component);
	target.remove();
});

describe('EmailCodeForm', () => {
	it('sends the email, then asks for the code and offers the inbox', async () => {
		type(target.querySelector('input[type=email]')!, 'grace@gmail.com');
		submit(target.querySelector('form')!);
		await tick();
		flushSync();
		expect(auth.signInWithMagicLink).toHaveBeenCalledWith('grace@gmail.com', undefined);
		expect(target.querySelector('input[autocomplete=one-time-code]')).not.toBeNull();
		expect(target.querySelector('a[href="https://mail.google.com/"]')).not.toBeNull();
	});

	it('verifies the 6 digits, ignoring spaces', async () => {
		type(target.querySelector('input[type=email]')!, 'grace@example.org');
		submit(target.querySelector('form')!);
		await tick();
		flushSync();
		type(target.querySelector('input[autocomplete=one-time-code]')!, '481 902');
		submit(target.querySelector('form')!);
		await tick();
		expect(auth.verifyEmailCode).toHaveBeenCalledWith('grace@example.org', '481902');
	});

	it('does not call Supabase for a short code', async () => {
		type(target.querySelector('input[type=email]')!, 'grace@example.org');
		submit(target.querySelector('form')!);
		await tick();
		flushSync();
		type(target.querySelector('input[autocomplete=one-time-code]')!, '123');
		submit(target.querySelector('form')!);
		await tick();
		flushSync();
		expect(auth.verifyEmailCode).not.toHaveBeenCalled();
		expect(target.querySelector('[role=alert]')?.textContent).not.toBe('');
	});
});
