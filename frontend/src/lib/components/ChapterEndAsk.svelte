<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { noteChapterEnd, shouldAsk, snoozeAsk } from '$lib/chapterAsk';
	import { localizeHref } from '$lib/href';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { openFrom, plainClick } from '$lib/signInSheet.svelte';
	import { planSchedules } from '$lib/planSchedules.svelte';
	import { askForPlanEmail } from '$lib/planEmail';

	/**
	 * Under the Next button at the end of a chapter, for a signed-out reader:
	 * their progress and streak live only on this device, and an account keeps
	 * them. Below Next, so going on reading stays the first thing. Timing and
	 * "Not now" live in $lib/chapterAsk.
	 *
	 * On a plan day with a tomorrow (`planSlug`), the same card offers the
	 * plan's daily email instead, which is the account's most concrete use:
	 * the choice is held and the sign-up panel opens (source `plan_day`); the
	 * email is turned on once the account exists ($lib/planEmail).
	 */
	let {
		title,
		chapterKey,
		planSlug
	}: {
		/** The book's (or plan's) title, for "Keep your place in …". */
		title: string;
		/** This chapter, e.g. "book:humility:3", to count chapter ends reached. */
		chapterKey: string;
		/** A plan day before the last: offer that plan's daily email. */
		planSlug?: string;
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
	// Read only inside {#if show}, i.e. in the browser: the chapter page is
	// prerendered, and SvelteKit forbids reading the query string there.
	const href = $derived(
		localizeHref(withSource(withSignup(loginHref($page.url.pathname, $page.url.search)), 'chapter_end'))
	);

	/** The plan whose email this card offers, or null for the account ask. */
	const planOffer = $derived(planSlug && !planSchedules.get(planSlug).email ? planSlug : null);
	// Read only inside {#if show}, like `href`.
	const planHref = $derived(
		localizeHref(withSource(withSignup(loginHref($page.url.pathname, $page.url.search)), 'plan_day'))
	);

	/**
	 * A plain click holds the plan's email and opens the panel; a modified one
	 * (new tab) or no JS follows the real /login link instead, as every
	 * sign-up prompt does (signInSheet.openFrom).
	 */
	function askPlan(e: MouseEvent, slug: string) {
		if (!plainClick(e)) return;
		e.preventDefault();
		askForPlanEmail(slug, 'plan_day');
	}

	function later() {
		snoozeAsk();
		dismissed = true;
	}
</script>

<span bind:this={anchor} aria-hidden="true"></span>
{#if show}
	<aside class="ask" aria-labelledby="ask-title" data-nosnippet>
		{#if planOffer}
			<p id="ask-title" class="font-semibold text-text">{t('plans.emailSignin')}</p>
			<p class="text-small text-muted">{t('plans.remindEmailHint')}</p>
		{:else}
			<p id="ask-title" class="font-semibold text-text">{t('reader.askTitle').replace('%title%', title)}</p>
			<p class="text-small text-muted">{t('reader.askBody')}</p>
		{/if}
		<div class="ask-row">
			{#if planOffer}
				{@const slug = planOffer}
				<a class="btn btn-primary btn-sm" href={planHref} use:seenOnView={'plan_day'} onclick={(e) => askPlan(e, slug)}
					>{t('plans.remindEmail')}</a
				>
			{:else}
				<a class="btn btn-primary btn-sm" {href} use:seenOnView={'chapter_end'} onclick={(e) => openFrom(e, 'chapter_end')}
					>{t('reader.askCta')}</a
				>
			{/if}
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
