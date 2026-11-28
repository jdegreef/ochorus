<script lang="ts">
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { formatLifespan, type AuthorBio, type BookSummary } from '$lib/library-public';
	import { subjectSlug, teacherNeeds } from '$lib/keyTeachings';
	import Portrait from '$lib/components/Portrait.svelte';

	/**
	 * The Key Teachings' "Find your teacher by need": a row of needs (learning
	 * to pray, suffering, doubt …) and, for the one chosen, the teachers who
	 * wrote most for it, each card opening their volume. A reader comes with a
	 * burden before they come with a name. The first need is open by default,
	 * so the section is never an empty prompt.
	 */
	let { books, authors }: { books: BookSummary[]; authors: AuthorBio[] } = $props();
	const t = i18n.t;

	const needs = $derived(teacherNeeds(books));
	let chosen = $state<string | null>(null);
	const current = $derived(needs.find((n) => n.id === chosen) ?? needs[0]);
	const bySlug = $derived(new Map(authors.map((a) => [a.slug, a])));
</script>

{#if needs.length > 1 && current}
	<section class="need mb-10" aria-labelledby="by-need">
		<h2 id="by-need" class="font-display text-h3 font-semibold">{t('series.needTitle')}</h2>
		<p class="mt-0.5 text-small text-muted">{t('series.needNote')}</p>
		<div class="chip-scroller mt-4" role="group" aria-label={t('series.needTitle')}>
			{#each needs as n (n.id)}
				<button
					type="button"
					class="chip"
					class:active={current.id === n.id}
					aria-pressed={current.id === n.id}
					onclick={() => (chosen = n.id)}
				>
					{t(n.k)}
				</button>
			{/each}
		</div>
		<ul class="teachers mt-5" aria-live="polite">
			{#each current.books as book (book.slug)}
				{@const slug = subjectSlug(book.slug)}
				{@const a = bySlug.get(slug)}
				{@const name = a?.name ?? book.cover_byline ?? book.title}
				<li>
					<a class="teacher card-lift" href={localizeHref(`/books/${book.slug}`)}>
						<Portrait
							{slug}
							{name}
							url={a?.photo_url ?? ''}
							px={56}
							decorative
							class="h-14 w-14 shrink-0"
						/>
						<span class="min-w-0">
							<span class="block font-display font-semibold text-text">{name}</span>
							{#if a}<span class="block text-small text-muted">
									{formatLifespan(a.birth_year, a.death_year, t('common.bornPrefix'))}
								</span>{/if}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.need {
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.teachers {
		display: grid;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	@media (min-width: 640px) {
		.teachers {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (min-width: 1024px) {
		.teachers {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	.teacher {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-bg);
		text-decoration: none;
	}
	.teacher:hover .text-text {
		color: var(--color-accent);
	}
</style>
