<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { auth } from '$lib/auth.svelte';
	import { accountHref } from '$lib/accountNav';
	import { welcome } from '$lib/welcome.svelte';
	import { readerActivity } from '$lib/readerActivity';
	import { readingGoal, GOAL_MIN, GOAL_MAX } from '$lib/readingGoal.svelte';
	import { readingMinutes } from '$lib/reading';
	import { bookChapterPath } from '$lib/reading-schema';
	import { authorPath } from '$lib/originals';
	import {
		STEP_COPY,
		WELCOME_EVENT,
		welcomeEventProps,
		welcomeSteps,
		type WelcomeAction,
		type WelcomeStepKey
	} from '$lib/welcomeSteps';
	import { track } from '$lib/analytics';
	import { getBook, getPlan, type BookDetail, type PlanDetail } from '$lib/library-public';
	import BookCover from '$lib/components/BookCover.svelte';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';

	/**
	 * Where a new account lands (HomeDashboard sends it here once; see
	 * welcome.svelte.ts). Two jobs: welcome the reader, and get one chapter read.
	 *
	 * Wide screens lead with the letter and the first-steps checklist; a phone
	 * leads with the one book to start with, so the first thing under a thumb
	 * is "Read Chapter 1". Same DOM either way: the two columns dissolve
	 * (`display: contents`) below lg and `order` re-stacks their cards.
	 *
	 * The starting book is Murray's Humility, which is published in every UI
	 * language, and `login.pitchSampleQuote` is already his line from its first
	 * chapter in each one. No English fallback (CLAUDE.md): if this language
	 * has no edition the card becomes "find your first book" instead.
	 */
	const t = i18n.t;
	const START_BOOK = 'humility-2';
	const START_PLAN = 'humility-12-days';
	const GOAL_DAYS = Array.from({ length: GOAL_MAX - GOAL_MIN + 1 }, (_, i) => GOAL_MIN + i);

	let book = $state<BookDetail | null>(null);
	let plan = $state<PlanDetail | null>(null);
	let loaded = $state(false);

	// The reading stores live in localStorage, not $state: re-read them on
	// mount and whenever a sign-in merge lands (`ochorus:sync`), the same way
	// OnboardingCard does.
	let ticks = $state(0);
	/** One analytics event per thing a new reader does here (see welcomeSteps). */
	const report = (action: WelcomeAction) => track(WELCOME_EVENT, welcomeEventProps(action, getLang()));

	onMount(() => {
		welcome.pageSeen();
		report('viewed');
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);

		const language = getLang();
		getBook(START_BOOK, language)
			.then((b) => (book = b.language === language ? b : null))
			.catch(() => (book = null))
			.finally(() => (loaded = true));
		getPlan(START_PLAN, language)
			.then((p) => (plan = p.language === language ? p : null))
			.catch(() => (plan = null));

		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const checklist = $derived.by(() => {
		void ticks;
		// Until the stored session is restored, assume the account step is done:
		// a reader on this page has almost always just signed up, and an unticked
		// "Create your account" would link them to the sign-up form for a moment.
		return welcomeSteps({ signedIn: !!auth.user || !auth.initialized, ...readerActivity(getLang()) });
	});

	const firstChapter = $derived(
		book?.chapters.length ? localizeHref(bookChapterPath(book.slug, book.chapters[0].order, false)) : null
	);
	const minutesEach = $derived(
		book?.chapters.length
			? readingMinutes(book.chapters.reduce((n, c) => n + c.word_count, 0) / book.chapters.length)
			: 0
	);
	/** Murray's own line from chapter 1, minus the highlight markers the login pitch uses. */
	const quote = $derived(t('login.pitchSampleQuote').replace(/\[\[|\]\]/g, ''));

	function stepHref(key: WelcomeStepKey): string {
		if (key === 'account') return accountHref('/welcome', false, true);
		if (key === 'save') return localizeHref('/books');
		return firstChapter ?? localizeHref('/books');
	}

	const KEEPS: { icon: IconName; title: string; body: string }[] = [
		{ icon: 'bookmark', title: 'welcomePage.keepPlace', body: 'welcomePage.keepPlaceBody' },
		{ icon: 'highlighter', title: 'welcomePage.keepNotes', body: 'welcomePage.keepNotesBody' },
		{ icon: 'calendar', title: 'welcomePage.keepPlans', body: 'welcomePage.keepPlansBody' },
		{ icon: 'heart', title: 'welcomePage.keepFree', body: 'welcomePage.keepFreeBody' }
	];
</script>

<svelte:head
	><title>{t('welcomePage.title')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head
>

<div class="page-col px-5 py-10">
	<PageHeader title={t('welcomePage.title')} tagline={t('welcomePage.tagline')} />

	<div class="welcome">
		<div class="col">
			<section class="letter" aria-labelledby="welcome-letter">
				<h2 id="welcome-letter" class="font-display text-h2">{t('welcomePage.letterTitle')}</h2>
				<div class="letter-body font-display text-body">
					<p>{t('welcomePage.letterP1')}</p>
					<p>{t('welcomePage.letterP2')}</p>
					<p>{t('welcomePage.letterP3')}</p>
				</div>
				<p class="mt-3 text-small text-muted">{t('welcomePage.letterSign')}</p>
			</section>

			<section class="start rounded-card border border-border bg-surface" aria-labelledby="welcome-start">
				{#if book && firstChapter}
					<div class="start-cover" aria-hidden="true"><BookCover {book} /></div>
					<div class="min-w-0">
						<p class="eyebrow text-gold">{t('welcomePage.startEyebrow')}</p>
						<h2 id="welcome-start" class="font-display mt-1 text-h2" lang={book.language}>{book.title}</h2>
						<p class="text-small text-muted">
							<a href={localizeHref(authorPath(book.author.slug))}>{book.author.name}</a>
						</p>
						{#if minutesEach}
							<p class="mt-1 text-small text-muted">
								{t('welcomePage.startMeta')
									.replace('%n%', String(book.chapters.length))
									.replace('%m%', String(minutesEach))}
							</p>
						{/if}
						<blockquote class="quote font-display text-body">{quote}</blockquote>
						<div class="mt-4 flex flex-wrap gap-3">
							<a
								class="btn btn-primary hover:no-underline"
								href={firstChapter}
								onclick={() => report('read first chapter')}
							>{t('welcomePage.readFirst')}</a>
							{#if plan}
								<a
									class="btn btn-ghost hover:no-underline"
									href={localizeHref(`/plans/${plan.slug}`)}
									onclick={() => report('follow plan')}
								>
									{t('welcomePage.followPlan').replace('%n%', String(plan.day_count))}
								</a>
							{/if}
						</div>
					</div>
				{:else if loaded}
					<div class="start-wide min-w-0">
						<h2 id="welcome-start" class="font-display text-h2">{t('welcomePage.browseTitle')}</h2>
						<p class="mt-1 text-body text-muted">{t('welcomePage.browseBody')}</p>
						<a
							class="btn btn-primary mt-4 hover:no-underline"
							href={localizeHref('/books')}
							onclick={() => report('browse library')}
						>
							{t('home.browseLibrary')}
						</a>
					</div>
				{:else}
					<div class="start-cover skeleton" aria-hidden="true"></div>
					<h2 id="welcome-start" class="sr-only">{t('welcomePage.startEyebrow')}</h2>
				{/if}
			</section>
		</div>

		<div class="col">
			<section class="steps rounded-card border border-border bg-surface" aria-labelledby="welcome-steps">
				<div class="flex items-baseline justify-between gap-3">
					<h2 id="welcome-steps" class="font-display text-h3">{t('welcomePage.stepsTitle')}</h2>
					<span class="count text-small">
						{t('welcomePage.stepsCount')
							.replace('%n%', String(checklist.done))
							.replace('%m%', String(checklist.steps.length))}
					</span>
				</div>
				<div class="bar" aria-hidden="true">
					<i style="width: {(checklist.done / checklist.steps.length) * 100}%"></i>
				</div>
				<ul class="step-list">
					{#each checklist.steps as step (step.key)}
						{@const copy = STEP_COPY[step.key]}
						<li>
							{#if step.done}
								<div class="step done">
									<span class="tick"><Icon name="check" size={14} /></span>
									<span class="text-body">{t(copy.title)}</span>
								</div>
							{:else}
								<a class="step" href={stepHref(step.key)} onclick={() => report(`step: ${step.key}`)}>
									<span class="tick"></span>
									<span class="min-w-0">
										<span class="block text-body font-semibold text-text">{t(copy.title)}</span>
										{#if copy.hint}<span class="block text-small text-muted">{t(copy.hint)}</span>{/if}
									</span>
									<Icon name="chevron-right" size={16} class="ms-auto shrink-0 text-muted" />
								</a>
							{/if}
						</li>
					{/each}
				</ul>
				{#if checklist.done === checklist.steps.length}
					<p class="text-small text-muted">{t('welcomePage.stepsDone')}</p>
				{/if}
			</section>

			<section class="goal rounded-card border border-border bg-surface-2" aria-labelledby="welcome-goal">
				<h2 id="welcome-goal" class="font-display text-h3">{t('welcomePage.goalTitle')}</h2>
				<p class="mt-1 text-small text-muted">{t('welcomePage.goalSub')}</p>
				<div class="seg mt-4 self-start" role="group" aria-label={t('settings.goalPerWeek')}>
					{#each GOAL_DAYS as n (n)}
						<button
							class:active={readingGoal.perWeek === n}
							aria-pressed={readingGoal.perWeek === n}
							onclick={() => {
								readingGoal.set(n);
								report(`goal: ${n}`);
							}}>{n}</button
						>
					{/each}
				</div>
			</section>
		</div>
	</div>

	<section class="mt-12 border-t border-border pt-8" aria-labelledby="welcome-keeps">
		<h2 id="welcome-keeps" class="section-label">{t('welcomePage.keepsTitle')}</h2>
		<ul class="keeps">
			{#each KEEPS as k (k.title)}
				<li>
					<span class="inline-flex items-center gap-2 text-body font-semibold">
						<span class="inline-flex text-gold"><Icon name={k.icon} size={20} /></span>{t(k.title)}
					</span>
					<span class="mt-1 block text-small text-muted">{t(k.body)}</span>
				</li>
			{/each}
		</ul>
	</section>

	<div class="mt-10">
		<a class="btn btn-ghost hover:no-underline" href={localizeHref('/')} onclick={() => report('go home')}
			>{t('welcomePage.goHome')}</a
		>
	</div>
</div>

<style>
	.welcome {
		display: grid;
		gap: 1.5rem;
	}
	/* Phone: the columns dissolve and the cards re-stack so the book comes
	   first — then the checklist, the letter, the goal. */
	.col {
		display: contents;
	}
	.start {
		order: 1;
	}
	.steps {
		order: 2;
	}
	.letter {
		order: 3;
	}
	.goal {
		order: 4;
	}
	@media (min-width: 1024px) {
		.welcome {
			grid-template-columns: minmax(0, 1fr) minmax(0, 22rem);
			gap: 3rem;
			align-items: start;
		}
		.col {
			display: flex;
			flex-direction: column;
			gap: 1.5rem;
		}
		.start,
		.steps,
		.letter,
		.goal {
			order: 0;
		}
	}

	.letter-body {
		display: grid;
		gap: 0.9rem;
		margin-top: 1rem;
		max-width: 40rem;
		line-height: 1.7;
	}

	.start {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: 1.25rem;
		align-items: start;
		padding: 1.25rem;
	}
	@media (min-width: 640px) {
		.start {
			grid-template-columns: 9rem minmax(0, 1fr);
			gap: 1.5rem;
			padding: 1.5rem;
		}
	}
	/* The no-book card has no cover: its text takes both columns. */
	.start-wide {
		grid-column: 1 / -1;
	}
	.start-cover.skeleton {
		aspect-ratio: 2 / 3;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.quote {
		margin: 1rem 0 0;
		padding-inline-start: 0.9rem;
		border-inline-start: 2px solid var(--gold);
		font-style: italic;
		line-height: 1.6;
	}

	.steps,
	.goal {
		display: flex;
		flex-direction: column;
		padding: 1.25rem;
	}
	.steps {
		gap: 0.75rem;
	}
	.bar {
		height: 4px;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		overflow: hidden;
	}
	.bar i {
		display: block;
		height: 100%;
		background: var(--accent);
		transition: width var(--duration-base) ease;
	}
	.step-list {
		display: grid;
		gap: 0.15rem;
	}
	.step {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.6rem 0.5rem;
		border-radius: var(--radius-sm);
		color: inherit;
		text-decoration: none;
	}
	a.step:hover {
		background: var(--surface-2);
	}
	.tick {
		display: inline-grid;
		flex: none;
		place-items: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		border: 1.5px solid var(--border-strong);
	}
	.step.done {
		color: var(--muted);
	}
	.step.done .tick {
		border-color: var(--accent);
		background: var(--accent);
		color: var(--accent-contrast);
	}

	.keeps {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		gap: 1.5rem;
		margin-top: 1rem;
	}
</style>
