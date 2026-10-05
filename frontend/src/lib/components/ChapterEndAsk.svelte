<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { noteChapterEnd, shouldAsk, snoozeAsk } from '$lib/chapterAsk';
	import { localizeHref } from '$lib/href';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { openFrom } from '$lib/signInSheet.svelte';

	/**
	 * Under the Next button at the end of a chapter, for a signed-out reader:
	 * their progress and streak live only on this device, and an account keeps
	 * them. Below Next, so going on reading stays the first thing. Timing and
	 * "Not now" live in $lib/chapterAsk.
	 */
	let {
		title,
		chapterKey,
		pathname,
		search
	}: {
		/** The book's (or plan's) title, for "Keep your place in …". */
		title: string;
		/** This chapter, e.g. "book:humility:3", to count chapter ends reached. */
		chapterKey: string;
		/** This page's localized path and query, for the sign-up's way back. */
		pathname: string;
		search: string;
	} = $props();

	const t = i18n.t;
	let dismissed = $state(false);
	/** Distinct chapter ends reached on this device, once this one is in view. */
	let ends = $state(0);
	let anchor = $state<HTMLElement>();
	const signedOut = $derived(auth.enabled && auth.initialized && !auth.user);

	// Count this chapter's end once the reader actually gets there, not when the
	// page opens: the card is about chapters read, not pages visited.
	$effect(() => {
		if (!anchor || !signedOut) return;
		const key = chapterKey;
		const io = new IntersectionObserver((entries) => {
			if (entries.some((e) => e.isIntersecting)) {
				ends = noteChapterEnd(key);
				io.disconnect();
			}
		});
		io.observe(anchor);
		return () => io.disconnect();
	});

	const show = $derived(signedOut && !dismissed && shouldAsk(ends));
	const href = $derived(
		localizeHref(withSource(withSignup(loginHref(pathname, search)), 'chapter_end'))
	);

	function later() {
		snoozeAsk();
		dismissed = true;
	}
</script>

<span bind:this={anchor} aria-hidden="true"></span>
{#if show}
	<aside class="ask" aria-labelledby="ask-title" data-nosnippet>
		<p id="ask-title" class="font-semibold text-text">{t('reader.askTitle').replace('%title%', title)}</p>
		<p class="text-small text-muted">{t('reader.askBody')}</p>
		<div class="ask-row">
			<a class="btn btn-primary btn-sm" {href} use:seenOnView={'chapter_end'} onclick={(e) => openFrom(e, 'chapter_end')}
				>{t('reader.askCta')}</a
			>
			<button type="button" class="btn btn-ghost btn-sm" onclick={later}>{t('reader.askLater')}</button>
		</div>
	</aside>
{/if}

<style>
	.ask {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		margin-top: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		padding: 1rem 1.1rem;
		text-align: start;
	}
	.ask-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.35rem;
	}
</style>
