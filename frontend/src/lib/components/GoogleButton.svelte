<script lang="ts">
	import GoogleMark from '$lib/components/GoogleMark.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/** "Continue with Google" — one button for /login and the sign-up panel. */
	let { onclick, disabled = false }: { onclick: () => void; disabled?: boolean } = $props();
	const t = i18n.t;
</script>

<button class="google-btn" type="button" {onclick} {disabled}>
	<GoogleMark />
	{t('login.google')}
</button>

<style>
	.google-btn {
		display: flex;
		width: 100%;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		padding: 0.6rem 1.1rem;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface-2);
		color: var(--text);
		font-family: var(--font-sans);
		font-weight: 600;
	}
	.google-btn:hover:not(:disabled) {
		background: var(--surface);
		border-color: var(--accent-soft-border);
	}
	.google-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
