<script lang="ts">
	import { SITE_URL, WHATSAPP_CHANNEL_URL } from '$lib/config';
	import { tIn } from '$lib/i18n.svelte';
	import { localeName } from '$lib/lang.svelte';
	import { locales } from '$lib/paraglide/runtime';
	import { loadTodayPicks } from '$lib/todayPicks';
	import { whatsappPost } from '$lib/whatsappPost';

	/**
	 * Today's WhatsApp post: the day's verse, reading and sermon (the home
	 * Today card's picks) written out for a WhatsApp channel in the chosen
	 * language, ready to copy and paste. Nothing is sent from here — the post
	 * goes out by hand from the channel. Pick a later date to prepare ahead;
	 * the links are the plain pages, which show each reader their own today.
	 * Internal tool: chrome is English-only; the post is in the language.
	 */

	/** YYYY-MM-DD for a date input, in local time. */
	const isoDay = (d: Date) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

	let language = $state('en');
	let day = $state(isoDay(new Date()));
	let post = $state('');
	let loading = $state(false);
	let failed = $state(false);
	let copied = $state(false);
	let textEl = $state<HTMLTextAreaElement>();

	/** An absolute link in the post's language (English carries no prefix). */
	const href = (lang: string) => (path: string) => `${SITE_URL}${lang === 'en' ? '' : `/${lang}`}${path}`;

	// Re-composed whenever the language or the date changes; a stale answer
	// (the admin changed the picker mid-fetch) is dropped.
	let asked = 0;
	$effect(() => {
		const lang = language;
		const [y, m, d] = day.split('-').map(Number);
		if (!y || !m || !d) return;
		const when = new Date(y, m - 1, d, 12);
		const ticket = ++asked;
		loading = true;
		failed = false;
		copied = false;
		void (async () => {
			try {
				const [picks, reading, sermon, chapter] = await Promise.all([
					loadTodayPicks(when, lang),
					tIn(lang, 'home.todayReading'),
					tIn(lang, 'home.sermonOfDay'),
					tIn(lang, 'home.todayChapter')
				]);
				if (ticket !== asked) return;
				const date = when.toLocaleDateString(lang, { weekday: 'long', day: 'numeric', month: 'long' });
				post =
					picks.verse || picks.reading || picks.sermon || picks.chapter
						? whatsappPost({ date, picks, labels: { reading, sermon, chapter }, href: href(lang) })
						: '';
			} catch {
				if (ticket === asked) failed = true;
			} finally {
				if (ticket === asked) loading = false;
			}
		})();
	});

	async function copy() {
		try {
			await navigator.clipboard.writeText(post);
			copied = true;
			setTimeout(() => (copied = false), 2500);
		} catch {
			// No clipboard: select the text so Ctrl+C copies it.
			textEl?.select();
		}
	}
</script>

<svelte:head><title>Admin · WhatsApp post — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<h1 class="text-h1">Today’s WhatsApp post</h1>
		<p class="mt-2 max-w-prose text-body text-muted">
			The day’s verse, reading and sermon of the day — the same picks as the home page’s Today card — written for a
			WhatsApp channel. Copy it and paste it into the channel. <b>*Bold*</b> and <i>_italic_</i> are WhatsApp’s own
			marks, and each link sits on its own line so WhatsApp shows a preview.
		</p>
	</header>

	<div class="flex flex-wrap items-end gap-3">
		<label class="text-small font-semibold">
			Language
			<select class="field mt-1 block text-small" bind:value={language}>
				{#each locales as code (code)}
					<option value={code}>{localeName(code)} ({code})</option>
				{/each}
			</select>
		</label>
		<label class="text-small font-semibold">
			Date
			<input class="field mt-1 block text-small" type="date" bind:value={day} />
		</label>
		<button type="button" class="btn btn-primary btn-sm" onclick={copy} disabled={!post || loading}>
			{copied ? 'Copied' : 'Copy post'}
		</button>
		<span class="sr-only" role="status">{copied ? 'Post copied' : ''}</span>
	</div>

	<div class="mt-6">
		{#if failed}
			<p class="text-body text-danger">Couldn’t load the day’s picks. Try again in a moment.</p>
		{:else if loading && !post}
			<p class="text-body text-muted">Composing…</p>
		{:else if !post}
			<p class="text-body text-muted">
				{localeName(language)} has no daily reading, verse or sermon yet, so there is nothing to post.
			</p>
		{:else}
			<textarea
				bind:this={textEl}
				class="field post w-full text-body"
				rows={Math.max(10, post.split('\n').length + 1)}
				readonly
				aria-label="The post"
				dir="auto"
				value={post}
			></textarea>
		{/if}
	</div>

	<p class="mt-6 text-small text-muted">
		{#if WHATSAPP_CHANNEL_URL}
			Readers are pointed to the channel at <a class="text-accent" href={WHATSAPP_CHANNEL_URL}>{WHATSAPP_CHANNEL_URL}</a>
			from /today and the footer.
		{:else}
			There is no public channel link yet. Once the channel exists, set <code>PUBLIC_WHATSAPP_CHANNEL_URL</code> on the
			ochorus-web service (render.yaml) and redeploy: a “Follow on WhatsApp” link then appears on /today and in the footer.
		{/if}
	</p>
</div>

<style>
	.post {
		font-family: var(--font-sans);
		white-space: pre-wrap;
		resize: vertical;
	}
</style>
