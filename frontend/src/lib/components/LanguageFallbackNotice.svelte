<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localeName } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import type { LanguageFallback } from '$lib/languageFallback';
	import type { Hreflang } from '$lib/seo';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * "Not yet available in हिन्दी — you're reading the English edition", with
	 * the editions that do exist and a way to what is available in the reader's
	 * language. Renders nothing when the page shows its own language. Dismissed
	 * for this view only: the next page that falls back is another work.
	 */
	let {
		fallback,
		alternates,
		browsePath,
		class: cls = 'mt-5'
	}: {
		fallback: LanguageFallback | null;
		/** The work's published editions, as hreflangFor builds them. */
		alternates: Hreflang['alternates'];
		/** The shelf for this kind of work (/books, /sermons, /plans, /articles). */
		browsePath: string;
		class?: string;
	} = $props();

	const t = i18n.t;
	let dismissed = $state(false);
</script>

{#if fallback && !dismissed}
	{@const want = localeName(fallback.requested)}
	<section
		class="fallback-notice relative rounded-card border border-border bg-surface-2 px-4 py-3 pe-12 {cls}"
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
			class="btn btn-icon btn-ghost absolute end-2 top-2"
			aria-label={t('a11y.close')}
			onclick={() => (dismissed = true)}><Icon name="close" /></button
		>
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
