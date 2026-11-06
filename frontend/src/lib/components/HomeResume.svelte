<script lang="ts" module>
	/**
	 * The block's space, held before the app runs. The home page is
	 * prerendered with the newcomer's hero; for a reader app.html's boot flag
	 * knows has a book open on this device (`data-home-resume`) HomeMarketing
	 * hides that hero and shows this frame in its place until the app has
	 * mounted, so the hero never flashes first. It is the block's own frame,
	 * drawn from the same snippets the block uses while a list is still on its
	 * way, with the plan's card only where the flag saw a started plan
	 * (`data-home-plan`).
	 */
	export { hold };
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import { currentBook } from '$lib/currentBook.svelte';
	import { planProgress } from '$lib/planProgress.svelte';
	import { todaysPlan, type PlanToday } from '$lib/todaysPlan';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * "Continue reading" for a returning reader who is not signed in (design
	 * #10): it takes the logged-out hero's place when this device has a book
	 * in progress. The book the reader is in — its cover, title, chapter, a
	 * thin meter and one Resume button to the chapter (the reader restores the
	 * paragraph from this device's anchor) — and, when a reading plan is under
	 * way, its day beside it.
	 *
	 * The book is `$lib/currentBook.svelte`, the one the signed-in hero wears,
	 * so the strip under this block (ContinueReading, told to leave it out)
	 * and the block can never show it twice. HomeMarketing mounts this only
	 * once that store has a key, so the block exists only with a book.
	 * The plan is `$lib/todaysPlan`, as the dashboard's "Today's reading"
	 * picks it — only a STARTED one, never an invitation.
	 */
	const t = i18n.t;

	const item = $derived(currentBook.item);
	const href = $derived(item ? localizeHref(item.href) : '');
	const chapter = $derived(item ? m.home_resume_chapter({ order: item.order, total: item.chapterCount }) : '');

	// A started plan's card is held from mount, so its arrival does not move
	// the page; it goes if the plan proves finished or the request fails.
	// Followed on `ochorus:sync`, as the book is (currentBook.watch), so the
	// two halves of the block cannot disagree after a sync or another tab.
	let plan = $state<PlanToday | null>(null);
	let planLoading = $state(false);
	let generation = 0;
	function loadPlan() {
		const mine = ++generation;
		if (!planProgress.started().length) {
			plan = null;
			planLoading = false;
			return;
		}
		planLoading = !plan;
		todaysPlan(getLang(), true)
			.then((p) => {
				if (mine === generation) plan = p;
			})
			.catch(() => {})
			.finally(() => {
				if (mine === generation) planLoading = false;
			});
	}
	onMount(() => {
		loadPlan();
		window.addEventListener('ochorus:sync', loadPlan);
		return () => window.removeEventListener('ochorus:sync', loadPlan);
	});
	const planDay = $derived(plan ? m.home_resume_plan_day({ day: plan.day, total: plan.plan.day_count }) : '');
</script>

{#snippet bookHold()}
	<div class="resume-card resume-book" aria-hidden="true">
		<div class="resume-cover aspect-[3/4] skeleton rounded-sm"></div>
		<div class="min-w-0 flex-1 self-center">
			<div class="resume-title font-display text-h3 font-semibold"><span class="inline-block w-3/4 skeleton rounded">&nbsp;</span></div>
			<div class="mt-0.5 text-small"><span class="inline-block w-1/2 skeleton rounded">&nbsp;</span></div>
			<div class="mt-3 text-small">&nbsp;</div>
			<div class="mt-1.5"><ProgressBar percent={0} label="" /></div>
			<div class="mt-4"><span class="btn btn-sm invisible">&nbsp;</span></div>
		</div>
	</div>
{/snippet}

{#snippet planHold()}
	<div class="resume-card resume-plan" aria-hidden="true">
		<div class="resume-title font-display text-body font-semibold"><span class="inline-block w-2/3 skeleton rounded">&nbsp;</span></div>
		<div class="mt-0.5 text-small"><span class="inline-block w-1/2 skeleton rounded">&nbsp;</span></div>
		<div class="mt-3"><ProgressBar percent={0} label="" /></div>
		<div class="mt-4"><span class="btn btn-sm invisible">&nbsp;</span></div>
	</div>
{/snippet}

{#snippet hold()}
	<section class="page-col px-5 pt-8 sm:pt-16" aria-hidden="true">
		<div class="eyebrow mb-3"><span class="inline-block w-28 skeleton rounded">&nbsp;</span></div>
		<div class="resume-grid">
			{@render bookHold()}
			<div class="resume-hold-plan">{@render planHold()}</div>
		</div>
	</section>
{/snippet}

<section class="page-col px-5 pt-8 sm:pt-16" aria-labelledby="home-resume" aria-busy={!item || planLoading}>
	<!-- The page's one <h1> while this block stands in for the hero (which
	     carries it otherwise, and is not rendered beside this). -->
	<h1 id="home-resume" class="eyebrow mb-3 text-accent">{t('home.resumeTitle')}</h1>
	<div class="resume-grid">
		{#if item}
			<div class="resume-card resume-book">
				<!-- The cover is the same way back in as the titled link beside it:
				     out of the tab order and hidden from a screen reader, so the
				     destination is announced once. -->
				<a {href} class="resume-cover" tabindex="-1" aria-hidden="true">
					<BookCover book={item.book} rounded="rounded-sm" priority />
				</a>
				<div class="min-w-0 flex-1 self-center">
					<div class="resume-title font-display text-h3 font-semibold">
						<a {href} class="line-clamp-2 text-text hover:no-underline">{item.title}</a>
					</div>
					<p class="mt-0.5 truncate text-small text-muted">{item.author}</p>
					<p class="mt-3 truncate text-small text-muted">{chapter}</p>
					<div class="mt-1.5"><ProgressBar percent={item.pct} label="{item.title}: {chapter}" /></div>
					<div class="mt-4">
						<a {href} class="btn btn-sm btn-primary btn-solid" aria-label="{t('home.resume')}: {item.title}"
							>{t('home.resume')}</a
						>
					</div>
				</div>
			</div>
		{:else}
			{@render bookHold()}
		{/if}
		{#if plan}
			<div class="resume-card resume-plan">
				<div class="resume-title font-display text-body font-semibold">
					<a href={localizeHref(`/plans/${plan.plan.slug}`)} class="line-clamp-2 text-text">{plan.plan.title}</a>
				</div>
				<p class="mt-0.5 truncate text-small text-muted" title={plan.chapterTitle || plan.bookTitle}>
					{planDay}{#if plan.chapterTitle || plan.bookTitle}<span class="sep mx-1.5">·</span>{plan.chapterTitle ||
							plan.bookTitle}{/if}
				</p>
				<div class="mt-3">
					<ProgressBar percent={(plan.done / plan.plan.day_count) * 100} label="{plan.plan.title}: {planDay}" />
				</div>
				<div class="mt-4">
					<a href={localizeHref(plan.href)} class="btn btn-sm btn-primary" aria-label="{t('home.resumePlan')}: {plan.plan.title}"
						>{t('home.resumePlan')}</a
					>
				</div>
			</div>
		{:else if planLoading}
			{@render planHold()}
		{/if}
	</div>
</section>

<style>
	/* Two columns from md whether or not a plan shows, so a plan's card that
	   is held and then proves finished leaves the book card where it was. */
	.resume-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1rem;
	}
	@media (min-width: 768px) {
		.resume-grid {
			grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		}
	}
	/* A phone's title often wraps: two lines are held in the frame and in the
	   block alike (the text sits on the lower one), so a long title does not
	   grow the card when the block replaces its frame. */
	@media (max-width: 639px) {
		.resume-title {
			display: flex;
			flex-direction: column;
			justify-content: flex-end;
			min-height: 2lh;
		}
	}
	.resume-card {
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		padding: 1.25rem;
	}
	.resume-book {
		display: flex;
		gap: 1.25rem;
	}
	.resume-plan {
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
	.resume-cover {
		display: block;
		width: 6rem;
		flex-shrink: 0;
	}
	@media (min-width: 640px) {
		.resume-card {
			padding: 1.5rem;
		}
		.resume-cover {
			width: 7rem;
		}
	}
	/* The hold's plan card shows only where the boot flag saw a started plan. */
	.resume-hold-plan {
		display: none;
	}
	:global(html[data-home-plan]) .resume-hold-plan {
		display: block;
	}
</style>
