<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { authErrorKey } from '$lib/authErrors';

	/**
	 * "Enter the code we emailed you" — how the phone app finishes a passwordless
	 * sign-in or a sign-up confirmation (`auth.emailCodes`). A link in an email
	 * cannot come back to the app, so the reader types the email's one-time code
	 * here instead. Success signs in through the auth listener; whoever shows this
	 * form leaves on `auth.user`, as after any sign-in.
	 */
	let {
		email,
		type
	}: {
		email: string;
		/** `email`: the magic-link / passwordless email; `signup`: the sign-up confirmation. */
		type: 'email' | 'signup';
	} = $props();

	const t = i18n.t;
	const uid = $props.id();

	let code = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		const err = await auth.verifyEmailCode(email, code, type);
		busy = false;
		if (err) error = t(authErrorKey(err));
	}
</script>

<form class="code-form" onsubmit={submit}>
	<label class="text-small font-medium text-muted" for="{uid}-code">{t('login.codeLabel')}</label>
	<!-- Supabase's codes are 6 digits by default (up to 10 if the project says
	     so). one-time-code lets iOS offer it from Mail above the keyboard. -->
	<input
		id="{uid}-code"
		type="text"
		inputmode="numeric"
		autocomplete="one-time-code"
		maxlength="16"
		required
		bind:value={code}
		aria-invalid={error ? 'true' : undefined}
		aria-describedby="{uid}-err"
		class="field code-field w-full"
	/>
	<!-- In the DOM before its text arrives, so a screen reader announces it. -->
	<p id="{uid}-err" role="alert" class="text-small text-danger">{error ?? ''}</p>
	<button class="btn btn-primary w-full" type="submit" disabled={busy} aria-busy={busy ? 'true' : undefined}>
		{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
		{t('login.codeSubmit')}
	</button>
</form>

<style>
	.code-form {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		text-align: start;
	}
	.code-form p:empty {
		margin-block-end: -0.6rem;
	}
	.code-field {
		font-variant-numeric: tabular-nums;
		letter-spacing: 0.3em;
		text-align: center;
	}
</style>
