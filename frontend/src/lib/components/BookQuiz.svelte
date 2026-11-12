<script lang="ts">
	import type { QuizQuestion } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Arrow from '$lib/components/Arrow.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import { quizScore } from '$lib/bookQuiz';

	/**
	 * The end-of-book quiz (`Book.quiz`): one question at a time, the answer
	 * and why straight after a pick, a score at the end to pass on. Shown by
	 * `BookFinished`, so only to a reader who has finished the book. Nothing is
	 * stored: it is a bit of fun at the end, not a record — Try again starts it
	 * over. Plain text throughout (the fixture's own words), so no {@html}.
	 */
	let {
		questions,
		bookTitle,
		slug,
		shareUrl,
		lang
	}: {
		questions: QuizQuestion[];
		bookTitle: string;
		/** For the "Read the chapter" link under each answer. */
		slug: string;
		/** The book's own page, absolute: what the score share passes on. */
		shareUrl: string;
		/** The questions' content language. */
		lang: string;
	} = $props();

	const t = i18n.t;
	let index = $state(0);
	/** The option picked for each question so far (index = question). */
	let picks = $state<number[]>([]);
	let done = $state(false);
	let heading = $state<HTMLElement>();

	const q = $derived(questions[index]);
	const picked = $derived<number | undefined>(picks[index]);
	const answered = $derived(picked !== undefined);
	const last = $derived(index === questions.length - 1);
	const score = $derived(quizScore(questions, picks));
	const progressLabel = $derived(
		t('quiz.progress').replace('%n%', String(index + 1)).replace('%t%', String(questions.length))
	);
	const scoreLine = $derived(
		t('quiz.score').replace('%n%', String(score)).replace('%t%', String(questions.length))
	);

	function pick(i: number) {
		if (answered) return;
		picks[index] = i;
	}
	function next() {
		if (last) done = true;
		else index++;
		// Keep the reader's place: focus moves to the new question (or the
		// score), which is announced, rather than staying on a button that went.
		queueMicrotask(() => heading?.focus());
	}
	function again() {
		picks = [];
		index = 0;
		done = false;
		queueMicrotask(() => heading?.focus());
	}
</script>

<section class="mt-10" aria-labelledby="quiz-heading">
	<h2 id="quiz-heading" class="section-heading">{t('quiz.heading')}</h2>
	<div class="quiz rounded-card border border-border bg-surface p-5 sm:p-6" {lang}>
		{#if !done}
			<p class="eyebrow text-muted">{progressLabel}</p>
			<div class="mt-2">
				<ProgressBar percent={((index + (answered ? 1 : 0)) / questions.length) * 100} label={progressLabel} />
			</div>
			<h3 bind:this={heading} tabindex="-1" class="font-display mt-4 text-h3 text-balance" dir="auto">{q.question}</h3>
			<div class="mt-4 flex flex-col gap-2" role="group" aria-label={q.question}>
				{#each q.options as option, i (i)}
					{@const right = answered && i === q.answer_index}
					{@const wrong = answered && i === picked && i !== q.answer_index}
					<button
						type="button"
						class="quiz-option"
						class:right
						class:wrong
						aria-pressed={i === picked}
						disabled={answered && !right && !wrong}
						aria-disabled={answered}
						onclick={() => pick(i)}
						dir="auto"
					>
						<span class="flex-1">{option}</span>
						{#if right}<span aria-hidden="true">✓</span>{:else if wrong}<span aria-hidden="true">✕</span>{/if}
					</button>
				{/each}
			</div>
			<div aria-live="polite">
				{#if answered}
					<p class="mt-4 text-small" dir="auto">
						<strong class:text-accent={picked === q.answer_index} class:text-danger={picked !== q.answer_index}
							>{picked === q.answer_index
								? t('quiz.correct')
								: t('quiz.wrong').replace('%a%', q.options[q.answer_index])}</strong
						>
						{q.explanation}
					</p>
				{/if}
			</div>
			{#if answered}
				<div class="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
					<button type="button" class="btn btn-primary btn-sm" onclick={next}>
						{last ? t('quiz.seeScore') : t('quiz.next')}
					</button>
					<a href={localizeHref(`/books/${slug}/${q.chapter}`)} class="text-small font-semibold text-accent hover:underline"
						>{t('quiz.readChapter')} <Arrow /></a
					>
				</div>
			{/if}
		{:else}
			<div class="text-center">
				<h3 bind:this={heading} tabindex="-1" class="font-display text-h2">{scoreLine}</h3>
				<p class="mt-1 text-small text-muted" dir="auto">{bookTitle}</p>
				<div class="mt-5 flex flex-wrap justify-center gap-2">
					<ShareButton
						url={shareUrl}
						title={t('quiz.shareTitle')
							.replace('%n%', String(score))
							.replace('%t%', String(questions.length))
							.replace('%title%', bookTitle)}
						showLabel
					/>
					<button type="button" class="btn btn-ghost btn-sm" onclick={again}>{t('quiz.again')}</button>
				</div>
			</div>
		{/if}
	</div>
</section>

<style>
	.quiz h3:focus {
		outline: none;
	}
	.quiz-option {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.7rem 0.9rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--bg);
		color: var(--text);
		text-align: start;
		font-size: var(--fs-body);
		cursor: pointer;
	}
	.quiz-option:hover:not([aria-disabled='true']) {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.quiz-option:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.quiz-option[aria-disabled='true'] {
		cursor: default;
	}
	.quiz-option:disabled {
		opacity: 0.5;
	}
	.quiz-option.right {
		border-color: var(--accent);
		background: var(--accent-soft);
		font-weight: 600;
	}
	.quiz-option.wrong {
		border-color: var(--danger);
		color: var(--danger);
	}
</style>
