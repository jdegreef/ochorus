<script lang="ts">
	import { cachedResumeBooks, libraryBooks, unfinishedBookSlugs } from '$lib/resumeBooks';
	import { getLang } from '$lib/lang.svelte';
	import type { ResumeItem } from '$lib/resumeItems';
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { allProgress } from '$lib/progress';
	import { buildResumeItems } from '$lib/resumeItems';
	import { chooseVariant, type SignupVariant } from '$lib/signupBand';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	/**
	 * The logged-out home's sign-up band — the site's one conversion prompt and
	 * the only place an email is captured (there is no separate newsletter).
	 *
	 * It runs FOUR bands at once, on purpose (see the PR's design note):
	 *  - a reader who already has local reading is TARGETED with the
	 *    progress-aware band ("don't lose what you've read");
	 *  - a first-time visitor is dropped into one of three A/B arms, uniformly and
	 *    stickily, so the arms stay comparable without an exposure denominator.
	 * Which arm was shown is remembered and attached to the sign-up (see
	 * `signupBand.ts` + `auth.signUp`), so the admin Users page can report which
	 * one earned each account.
	 *
	 * Gated exactly like AccountCta: `auth.enabled` is false during prerender
	 * (browser-only), so the band never bakes into the indexed HTML and appears
	 * only client-side once we know the reader is signed out. The reader's place
	 * comes from the local progress cache, read after mount.
	 */
	const t = i18n.t;
	const signupHref = $derived(`${localizeHref('/login')}?mode=signup`);

	let decided = $state(false);
	// Set synchronously when the effect below starts deciding, so a re-run while
	// the book list is in flight (auth settling) cannot decide twice.
	let deciding = false;
	let variant = $state<SignupVariant>('keep');
	let topBook = $state<ResumeItem | null>(null);

	// A genuine side effect: it reads localStorage (progress + the sticky arm),
	// may draw a random arm, and PERSISTS the shown arm for sign-up attribution —
	// so it is not a $derived in disguise. Runs once, only when we know the reader
	// is signed out (so we never attribute or reshuffle for a signed-in visitor),
	// and re-checks if auth resolves after mount.
	$effect(() => {
		if (!auth.enabled || !auth.initialized || auth.user || decided || deciding) return;
		deciding = true;
		const progress = allProgress();
		const hasProgress = progress.some((p) => p.finished_at == null);
		variant = chooseVariant(hasProgress);
		// The caption names the reader's book, and it is drawn ONCE: from the
		// cached summaries of their in-progress books when those have it, else
		// after the book list lands — never a generic caption that is then
		// rewritten in place. Only unfinished BOOK progress needs the list; the
		// caption never waits on sermons. See `$lib/resumeBooks`.
		const pick = (books: Parameters<typeof buildResumeItems>[0]) =>
			buildResumeItems(books, [], progress).find((i) => !i.finished) ?? null;
		const lang = getLang();
		const readingABook = unfinishedBookSlugs(progress).length > 0;
		topBook = readingABook ? pick(cachedResumeBooks(lang)) : null;
		if (topBook || !readingABook) {
			decided = true;
			return;
		}
		libraryBooks(lang)
			.then((books) => (topBook = pick(books)))
			.catch(() => {})
			.finally(() => (decided = true));
	});

	const show = $derived(auth.enabled && auth.initialized && !auth.user && decided);

	// Option 1's three concrete keeps, each with an icon so the value reads fast.
	const keepBenefits: { icon: IconName; label: string }[] = [
		{ icon: 'bookmark', label: 'home.signupKeepB1' },
		{ icon: 'sparkle', label: 'home.signupKeepB2' },
		{ icon: 'flame', label: 'home.signupKeepB3' }
	];

	const topPct = $derived(topBook && topBook.pct != null ? Math.round(topBook.pct) : null);
</script>

<!-- The CTA column every variant ends with: primary button + reassurance line,
     differing only in their two message keys. -->
{#snippet cta(ctaKey: string, microKey: string)}
	<div class="flex flex-col items-stretch gap-2 text-center">
		<a class="btn btn-primary" href={signupHref}>{t(ctaKey)}</a>
		<span class="text-small text-muted">{t(microKey)}</span>
	</div>
{/snippet}

{#if show}
	<section class="mt-14 border-y border-border bg-surface-2">
		<div class="mx-auto max-w-4xl px-5 py-12">
			{#if variant === 'progress'}
				<!-- Option 2 · progress-targeted (returning, signed-out reader) -->
				<div class="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-center">
					<div>
						<p class="eyebrow mb-2 flex items-center gap-1.5 text-accent">
							<Icon name="bookmark" size={15} />
							{t('home.signupProgressEyebrow')}
						</p>
						<h2 class="text-h2 mb-2">{t('home.signupProgressTitle')}</h2>
						<p class="mb-4 max-w-xl text-body text-muted">{t('home.signupProgressText')}</p>
						{#if topBook && topPct != null}
							<div class="max-w-sm">
								<div class="h-2 overflow-hidden rounded-full bg-accent-soft">
									<div class="h-full rounded-full bg-accent" style="width: {topPct}%"></div>
								</div>
								<p class="mt-1.5 text-small text-muted">
									<span class="text-text">{topBook.title}</span> · {topPct}%
								</p>
							</div>
						{/if}
					</div>
					{@render cta('home.signupProgressCta', 'home.signupMicroFree')}
				</div>
			{:else if variant === 'habit'}
				<!-- Option 3 · the devotional habit -->
				<div class="grid gap-6 sm:grid-cols-[auto_1fr_auto] sm:items-center">
					<div class="flex items-end gap-1.5" aria-hidden="true" style="height: 3.25rem">
						{#each [40, 62, 52, 80, 70, 95, 58] as h, i (i)}
							<span
								class="w-2.5 rounded-sm {i < 5 ? 'bg-accent' : 'bg-accent-soft'}"
								style="height: {h}%"
							></span>
						{/each}
					</div>
					<div>
						<h2 class="text-h2 mb-2">{t('home.signupHabitTitle')}</h2>
						<p class="max-w-xl text-body text-muted">{t('home.signupHabitText')}</p>
					</div>
					{@render cta('home.signupHabitCta', 'home.signupMicroFree')}
				</div>
			{:else if variant === 'library'}
				<!-- Option 4 · the whole library, kept -->
				<div class="grid gap-6 sm:grid-cols-[auto_1fr_auto] sm:items-center">
					<div class="flex items-end gap-1" aria-hidden="true" style="height: 3.5rem">
						{#each [82, 100, 90, 96, 78] as h, i (i)}
							<span
								class="w-3.5 rounded-t-sm {i === 1 ? 'bg-gold' : 'bg-accent'}"
								style="height: {h}%"
							></span>
						{/each}
					</div>
					<div>
						<p class="eyebrow mb-2 text-gold">{t('home.signupMicroFree')}</p>
						<h2 class="text-h2 mb-2">{t('home.signupLibraryTitle')}</h2>
						<p class="max-w-xl text-body text-muted">{t('home.signupLibraryText')}</p>
					</div>
					{@render cta('home.signupLibraryCta', 'home.signupMicroSeconds')}
				</div>
			{:else}
				<!-- Option 1 · name what you keep (default first-visit arm) -->
				<div class="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-center">
					<div>
						<h2 class="text-h2 mb-4">{t('home.signupKeepTitle')}</h2>
						<ul class="flex flex-col gap-2.5 sm:flex-row sm:flex-wrap sm:gap-x-6">
							{#each keepBenefits as b (b.label)}
								<li class="flex items-center gap-2.5 text-body">
									<span
										class="flex h-8 w-8 shrink-0 items-center justify-center rounded-card border border-accent-soft-border bg-accent-soft text-accent"
									>
										<Icon name={b.icon} size={17} />
									</span>
									{t(b.label)}
								</li>
							{/each}
						</ul>
					</div>
					{@render cta('home.signupKeepCta', 'home.signupMicroFull')}
				</div>
			{/if}
		</div>
	</section>
{/if}
