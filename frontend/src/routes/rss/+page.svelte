<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { hreflangAll } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	// The footer's "RSS" link used to point straight at /feed.xml, which a
	// browser renders as a raw XML tree under "This XML file does not appear to
	// have any style information" — to anyone who doesn't already use a feed
	// reader, that reads as a broken page. This is the human front door: what a
	// feed is, and the address to paste. Feed readers never needed the footer
	// link — they find the feed through the <link rel="alternate"> in every
	// page's <head> (routes/+layout.svelte), which this page carries too.
	// (A styled feed via XSLT was the other option; Chrome is removing XSLT.)
	const path = '/rss/';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const feedUrl = `${SITE_URL}/feed.xml`;

	let copied = $state(false);
	let copyTimer: ReturnType<typeof setTimeout> | undefined;

	async function copyFeedUrl() {
		try {
			await navigator.clipboard.writeText(feedUrl);
			copied = true;
			clearTimeout(copyTimer);
			copyTimer = setTimeout(() => (copied = false), 1500);
		} catch {
			// Clipboard blocked: the address is on screen and selectable.
		}
	}
</script>

<Seo
	title="{t('rss.title')} — Ochorus"
	description={t('rss.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/default.png"
/>

<div class="reading-page">
	<p class="eyebrow mb-2 text-accent">RSS</p>
	<h1 class="text-h1 mb-6">{t('rss.heading')}</h1>

	<p class="text-body text-muted">{t('rss.intro')}</p>

	<div class="mt-8 rounded-card border border-border bg-surface-2 p-6">
		<h2 class="text-h2 mb-1">{t('rss.urlLabel')}</h2>
		<p class="mb-4 text-small text-muted">{t('rss.urlSub')}</p>
		<div class="flex flex-wrap items-center gap-3">
			<code class="feed-url text-small">{feedUrl}</code>
			<button type="button" class="btn btn-primary" onclick={copyFeedUrl} aria-live="polite">
				{copied ? t('share.linkCopied') : t('share.copyLink')}
			</button>
		</div>
		<!-- The feed is English-only (routes/feed.xml), so say so where the reader
		     isn't reading in English rather than let them subscribe and wonder. -->
		{#if lang.current !== 'en'}
			<p class="mt-4 text-small text-muted">{t('rss.englishOnly')}</p>
		{/if}
	</div>

	<div class="mt-4 rounded-card border border-border p-6">
		<h2 class="text-h2 mb-1">{t('rss.whatTitle')}</h2>
		<p class="text-small text-muted">{t('rss.whatBody')}</p>
	</div>

	<p class="mt-8 text-small text-muted">
		<a href="/feed.xml" class="underline hover:text-text">{t('rss.rawLink')}</a>
	</p>
</div>

<style>
	.feed-url {
		overflow-wrap: anywhere;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg);
		user-select: all;
	}
</style>
