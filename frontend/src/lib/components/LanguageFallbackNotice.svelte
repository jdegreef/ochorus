<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localeName } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import type { LanguageFallback } from '$lib/languageFallback';
	import type { Hreflang } from '$lib/seo';

	/**
	 * "Not yet available in हिन्दी — you're reading the English edition."
	 *
	 * Shown when a page renders another language's edition than its URL asks for
	 * (see languageFallback). It offers the editions that do exist — the same
	 * hreflang set the book page's "Read in your language" pills use — and a way
	 * to what IS available in the reader's language.
	 *
	 * Dismissable for the rest of this view only: the next page that falls back
	 * says so again, because each one is a different work.
	 */
	let {
		fallback,
		alternates,
		browsePath
	}: {
		fallback: LanguageFallback;
		/** The work's published editions, as hreflangFor builds them. */
		alternates: Hreflang['alternates'];
		/** The shelf for this kind of work (/books, /sermons, /plans). */
		browsePath: string;
	} = $props();

	const t = i18n.t;
	let dismissed = $state(false);
	const want = $derived(localeName(fallback.requested));
</script>

{#if !dismissed}
	<section
		class="fallback-notice relative mb-6 rounded-card border border-border bg-surface-2 px-4 py-3 pe-12"
		role="status"
		aria-labelledby="fallback-title"
	>
		<h2 id="fallback-title" class="text-small font-semibold text-text">
			{t('fallback.title').replace('%lang%', want)}
		</h2>
		<p class="mt-1 text-small text-muted">
			{t('fallback.body').replace('%lang%', localeName(fallback.shown))}
		</p>
		{#if alternates.length > 1}
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<span class="text-small text-muted">{t('fallback.alsoIn')}</span>
				<!-- Full loads, like the book page's pills: the locale comes from the
				     URL, and a client-side nav keeps the old one. -->
				{#each alternates as ed (ed.loc)}
					<a
						href={ed.href}
						class="tag"
						hreflang={ed.loc}
						lang={ed.loc}
						aria-current={ed.loc === fallback.shown ? 'page' : undefined}
						data-sveltekit-reload>{localeName(ed.loc)}</a
					>
				{/each}
			</div>
		{/if}
		<a href={localizeHref(browsePath)} class="mt-3 inline-block text-small font-semibold">
			{t('fallback.browse').replace('%lang%', want)}
		</a>
		<button
			class="btn-icon absolute end-2 top-2"
			aria-label={t('a11y.close')}
			onclick={() => (dismissed = true)}
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
		</button>
	</section>
{/if}

<style>
	/* The edition on screen, among the ones on offer. */
	.fallback-notice .tag[aria-current='page'] {
		border-color: var(--accent);
		color: var(--accent);
		font-weight: 600;
	}
</style>
