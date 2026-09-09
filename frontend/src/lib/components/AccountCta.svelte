<script lang="ts">
	import { auth } from '$lib/auth.svelte';

	/**
	 * A logged-out-only prompt to create a free Ochorus account — the site's one
	 * conversion funnel, and the one place an email is captured: there is no
	 * separate newsletter, so account sign-up IS the list.
	 *
	 * Reading here never needs an account (the quote pages say as much), so the
	 * copy sells what an account actually adds — following writers/themes and
	 * cross-device sync — not access. `action` names the follow verb that fits the
	 * host page.
	 *
	 * English literal, for the same reason its host pages are (page-design F3):
	 * it is shown on the English-only quote pages. When it later lands on
	 * localized pages, the strings move to the message catalogue.
	 *
	 * Gated on `auth.initialized` so the prerendered HTML (auth unresolved on the
	 * server) and a signed-in reader both render nothing — the card appears only
	 * client-side, once we know the reader is signed out. `auth` is inert when
	 * unconfigured (`auth.enabled` false), so it also stays hidden then.
	 */
	interface Props {
		/** The follow verb for the host page, e.g. "follow the writers you love". */
		action?: string;
	}
	let { action = 'follow the writers and themes you love' }: Props = $props();

	const show = $derived(auth.enabled && auth.initialized && !auth.user);
</script>

{#if show}
	<aside class="account-cta">
		<div class="cta-text">
			<h2 class="cta-h">Keep what you find</h2>
			<p class="cta-p">
				Reading here is always free and needs no account. Create one to {action} — and keep your
				highlights and place in sync across every device. No cost, no ads.
			</p>
		</div>
		<a class="btn btn-primary" href="/login?mode=signup">Create a free account</a>
	</aside>
{/if}

<style>
	/* Mirrors the article "Read next" aside (same page family, proven tokens):
	   a quiet bordered surface card, not a loud banner. */
	.account-cta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1rem 1.5rem;
		margin-top: 2.5rem;
		padding: 1.25rem 1.4rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-surface);
	}
	.cta-text {
		min-width: 0;
	}
	.cta-h {
		margin: 0 0 0.3rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		color: var(--color-text);
	}
	.cta-p {
		margin: 0;
		max-width: 42rem;
		font-size: var(--fs-small);
		line-height: 1.5;
		color: var(--color-muted);
	}
</style>
