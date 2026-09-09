<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * A logged-out-only prompt to create a free Ochorus account — the site's one
	 * conversion funnel, and the one place an email is captured: there is no
	 * separate newsletter, so account sign-up IS the list.
	 *
	 * The copy is the SAME account band the home page shows
	 * (`home.signupTitle` / `login.syncNote` / `login.createAccountLink`), so it
	 * reads consistently everywhere and is already translated in every catalogue —
	 * no new message keys, and it localizes on the localized pages (articles,
	 * hubs) rather than pinning one language. Reading never needs an account; the
	 * value sold is sync across devices, not access.
	 *
	 * Gated on `auth.initialized` so the prerendered HTML (auth unresolved on the
	 * server) and a signed-in reader both render nothing — the card appears only
	 * client-side once we know the reader is signed out. Inert when auth is
	 * unconfigured (`auth.enabled` false).
	 */
	const t = i18n.t;
	const show = $derived(auth.enabled && auth.initialized && !auth.user);
</script>

{#if show}
	<aside class="account-cta">
		<div class="cta-text">
			<h2 class="cta-h">{t('home.signupTitle')}</h2>
			<p class="cta-p">{t('login.syncNote')}</p>
		</div>
		<a class="btn btn-primary shrink-0" href="{localizeHref('/login')}?mode=signup">
			{t('login.createAccountLink')}
		</a>
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
