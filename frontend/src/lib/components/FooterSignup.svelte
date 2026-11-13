<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { noteSignupSource, seenOnView, signupStarted, withSource } from '$lib/signupSource';
	import { openFrom, signInSheet } from '$lib/signInSheet.svelte';
	import { allProgress } from '$lib/progress';
	import { cachedResumeBooks, unfinishedBookSlugs } from '$lib/resumeBooks';
	import { buildResumeItems, type ResumeBook } from '$lib/resumeItems';
	import { adventOffer, chooseFooterPitch, footerPage, FOOTER_SOURCE } from '$lib/footerSignup';
	import BookCover from '$lib/components/BookCover.svelte';
	import GoogleMark from '$lib/components/GoogleMark.svelte';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	/**
	 * The footer's sign-up card for a signed-out reader (design: "Ochorus Footer
	 * Sign-up", 2026-11): one slot that shows the strongest reason for THIS
	 * reader on THIS page ($lib/footerSignup) — the book they're reading, the
	 * work on the page, Advent, or what an account keeps — with two ways in
	 * side by side: Google in one tap, and the sign-up sheet (email, or Google
	 * again) without leaving the page. Each message signs up under its own
	 * source, so the admin Users page can tell them apart.
	 *
	 * Loaded lazily by SiteFooter (only signed-out readers see it, and only in
	 * the browser), so none of this rides in every page's entry bundle.
	 */
	const t = i18n.t;

	// The book in progress: from this device's progress and the cached book
	// list only — no fetch for a footer. No cached list, no book: the next
	// message down takes the slot. Read once, as the card is created: it only
	// ever renders in the browser (SiteFooter loads it for a signed-out reader
	// after mount), so the first paint is already the right message rather
	// than the general band swapping out a frame later.
	const today = new Date();
	function bookInProgress(): ResumeBook | null {
		const progress = allProgress();
		if (!unfinishedBookSlugs(progress).length) return null;
		return (
			buildResumeItems(cachedResumeBooks(getLang()), [], progress).find(
				(i): i is ResumeBook => i.kind === 'book' && !i.finished
			) ?? null
		);
	}
	const book = bookInProgress();

	const here = $derived(footerPage($page.route.id, ($page.data ?? {}) as Record<string, unknown>));
	const advent = adventOffer(today);
	const pitch = $derived(chooseFooterPitch({ hasProgressBook: !!book, page: here, inSeason: !!advent }));
	const source = $derived(FOOTER_SOURCE[pitch]);
	const returnTo = $derived($page.url.pathname + $page.url.search);
	const signupHref = $derived(withSource(withSignup(loginHref($page.url.pathname, $page.url.search)), source));

	const pct = $derived(book ? Math.round(book.pct) : 0);
	const adventDate = $derived(
		advent
			? new Date(advent.start * 86_400_000).toLocaleDateString(getLang(), {
					day: 'numeric',
					month: 'long',
					timeZone: 'UTC'
				})
			: ''
	);

	const title = $derived.by(() => {
		if (pitch === 'progress') return t('home.signupProgressTitle');
		if (pitch === 'season') return t('calendar.adventTitle');
		if (pitch === 'band') return t('home.signupKeepTitle');
		if (!here) return '';
		if (here.kind === 'sermon') return t('footer.ctaSermonTitle').replace('%title%', here.title);
		if (here.kind === 'author') return t('footer.ctaAuthorTitle').replace('%name%', here.name);
		return t('footer.ctaBookTitle').replace('%title%', here.title);
	});
	const text = $derived.by(() => {
		if (pitch === 'progress') return t('home.signupProgressText');
		if (pitch === 'season') return t('footer.ctaSeasonText');
		if (pitch === 'band') return '';
		if (!here) return '';
		if (here.kind === 'sermon') return t('footer.ctaSermonText');
		if (here.kind === 'author') return t('footer.ctaAuthorText');
		if (here.kind === 'plan') return t('footer.ctaPlanText');
		return t('footer.ctaBookText');
	});
	const cta = $derived(pitch === 'progress' ? t('home.signupProgressCta') : t('home.signupKeepCta'));

	const benefits: { icon: IconName; label: string }[] = [
		{ icon: 'bookmark', label: 'home.signupKeepB1' },
		{ icon: 'sparkle', label: 'home.signupKeepB2' },
		{ icon: 'flame', label: 'home.signupKeepB3' }
	];

	// Google, straight from the footer: the source is noted first, as the sheet
	// notes it on opening, so the account is credited to this message. If the
	// redirect can't start, the sheet opens instead, where the error can show.
	let busy = $state(false);
	let started = false;
	async function google() {
		busy = true;
		noteSignupSource(source);
		// One start per reader, as SignUpForm counts it: a second press after
		// a cancelled consent screen is the same attempt.
		if (!started) signupStarted();
		started = true;
		const err = await auth.signInWithGoogle(returnTo);
		busy = false;
		if (err) signInSheet.show(source);
	}
</script>

<div class="signup" data-pitch={pitch}>
	<div class="signup-main">
		{#if pitch === 'progress' && book}
			<div class="signup-art" aria-hidden="true"><BookCover book={book.book} rounded="rounded-sm" /></div>
		{/if}
		<div class="min-w-0">
			{#if pitch === 'progress'}
				<p class="eyebrow mb-1 text-accent">{t('home.signupProgressEyebrow')}</p>
			{:else if pitch === 'season' && advent}
				<p class="eyebrow mb-1 text-accent">
					{advent.daysToGo ? t('footer.ctaSeasonStarts').replace('%date%', adventDate) : t('calendar.todayDoor')}
				</p>
			{/if}
			<p class="signup-title" dir="auto">{title}</p>
			{#if pitch === 'progress' && book}
				<div class="mt-2 max-w-sm">
					<div class="h-1.5 overflow-hidden rounded-full bg-accent-soft">
						<div class="h-full rounded-full bg-accent" style:width="{pct}%"></div>
					</div>
					<p class="mt-1 truncate text-small text-muted"><span class="text-text">{book.title}</span> · {pct}%</p>
				</div>
			{:else if text}
				<p class="mt-1 max-w-xl text-small text-muted">{text}</p>
			{/if}
			{#if pitch === 'season'}
				<a class="mt-2 inline-block text-small font-semibold text-accent" href="{localizeHref('/today')}#calendar"
					>{t('calendar.seeDoors')}</a
				>
			{/if}
		</div>
		<div class="signup-actions">
			<a
				href={localizeHref(signupHref)}
				class="btn signup-cta"
				use:seenOnView={source}
				onclick={(e) => openFrom(e, source)}
			>
				<span>{cta}</span>
				<Icon name="chevron-right" size={16} class="signup-arrow" mirror={false} />
			</a>
			{#if auth.enabled}
				<button type="button" class="btn btn-ghost signup-google" onclick={google} disabled={busy}>
					<GoogleMark />
					{t('login.google')}
				</button>
			{/if}
			<p class="text-center text-small text-muted">{t('home.signupMicroFull')}</p>
		</div>
	</div>
	{#if pitch === 'band'}
		<ul class="signup-benefits" role="list">
			{#each benefits as b (b.label)}
				<li><Icon name={b.icon} size={18} /><span>{t(b.label)}</span></li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	/* One framed card lifted off the footer's tint. The general band wears the
	   accent's soft ground and its three keeps; the targeted messages sit on
	   the surface, so the one about THIS reader reads as personal. */
	.signup {
		padding: 1.25rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.signup[data-pitch='band'] {
		border-color: var(--accent-soft-border);
		background: var(--accent-soft);
	}
	@media (min-width: 640px) {
		.signup {
			padding: 1.5rem 1.75rem;
		}
	}
	.signup-main {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1rem 1.5rem;
		align-items: center;
	}
	.signup-main:has(.signup-art) {
		grid-template-columns: auto minmax(0, 1fr);
	}
	.signup-art {
		inline-size: 3.5rem;
	}
	.signup-actions {
		grid-column: 1 / -1;
		display: grid;
		gap: 0.5rem;
	}
	@media (min-width: 768px) {
		.signup-main,
		.signup-main:has(.signup-art) {
			grid-template-columns: minmax(0, 1fr) minmax(14rem, auto);
		}
		.signup-main:has(.signup-art) {
			grid-template-columns: auto minmax(0, 1fr) minmax(14rem, auto);
		}
		.signup-actions {
			grid-column: auto;
		}
	}
	.signup-title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h3);
		line-height: 1.2;
		color: var(--text);
		text-wrap: balance;
	}
	.signup-google {
		justify-content: center;
		background: var(--surface);
	}
	.signup-benefits {
		display: grid;
		gap: 0.5rem 1.5rem;
		margin: 1.25rem 0 0;
		padding: 1rem 0 0;
		list-style: none;
		border-block-start: 1px solid var(--accent-soft-border);
		font-size: var(--fs-small);
		color: var(--text);
	}
	@media (min-width: 640px) {
		.signup-benefits {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	.signup-benefits li {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.signup-benefits :global(svg) {
		flex: none;
		color: var(--accent);
	}

	/* The deliberately LOUD conversion control, carried over from the footer's
	   old invite: solid indigo with a thin gold ring (the signature pairing) and
	   a warm sweep on hover. A .btn-primary is soft by design (STYLE_GUIDE §5);
	   this is the named exception. Scoped and unlayered, so it beats @layer
	   components and changes nothing else. */
	.signup-cta {
		position: relative;
		overflow: hidden;
		isolation: isolate;
		justify-content: center;
		text-decoration: none;
		color: var(--accent-contrast);
		background: var(--accent);
		box-shadow:
			inset 0 0 0 1px var(--gold),
			0 7px 18px -9px var(--accent);
		transition:
			transform var(--duration-fast) ease,
			box-shadow var(--duration-fast) ease,
			filter var(--duration-fast) ease;
	}
	.signup-cta span,
	.signup-cta :global(.signup-arrow) {
		position: relative;
		z-index: 2;
	}
	.signup-cta :global(.signup-arrow) {
		transition: transform var(--duration-fast) ease;
	}
	.signup-cta::after {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 1;
		background: linear-gradient(115deg, transparent 35%, color-mix(in srgb, var(--gold) 45%, transparent) 50%, transparent 65%);
		transform: translateX(-130%);
		pointer-events: none;
	}
	.signup-cta:hover {
		text-decoration: none;
		transform: translateY(-1px);
		filter: brightness(1.04);
		box-shadow:
			inset 0 0 0 1px var(--gold),
			0 11px 24px -9px var(--accent);
	}
	.signup-cta:hover::after {
		animation: signup-sheen 0.85s ease;
	}
	.signup-cta:hover :global(.signup-arrow) {
		transform: translateX(3px);
	}
	:global([dir='rtl']) .signup-cta :global(.signup-arrow) {
		transform: scaleX(-1);
	}
	:global([dir='rtl']) .signup-cta:hover :global(.signup-arrow) {
		transform: scaleX(-1) translateX(3px);
	}
	@keyframes signup-sheen {
		to {
			transform: translateX(130%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.signup-cta,
		.signup-cta :global(.signup-arrow) {
			transition: none;
		}
		.signup-cta:hover,
		.signup-cta:hover :global(.signup-arrow) {
			transform: none;
		}
		.signup-cta:hover::after {
			animation: none;
		}
	}
</style>
