<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import type { ProgressRecord, WorkKind } from '$lib/reading-schema';
	import { finishedPlates, plateDate, plateName, plateStyle } from '$lib/bookplate';
	import { auth } from '$lib/auth.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Bookplate from '$lib/components/Bookplate.svelte';
	import BookplateNameField from '$lib/components/BookplateNameField.svelte';
	import BookplateSave from '$lib/components/BookplateSave.svelte';

	/**
	 * "Bookplates" on the Bookshelf: a plate for every finished book, newest
	 * first, like the inside covers of a family's books. Nothing is stored for
	 * them — each is the finished stamp the shelf already reads, made out to the
	 * account's name. The Bookshelf is signed-in only, so the one missing piece
	 * can be a display name, which the reader writes once above the plates.
	 */
	let { progress, books }: { progress: (ProgressRecord & { slug: string; kind: WorkKind })[]; books: BookSummary[] } =
		$props();
	const t = i18n.t;
	const FIRST = 6;

	const plates = $derived(finishedPlates(progress, books));
	const name = $derived(plateName(auth.displayName));
	const locale = getLang();
	let all = $state(false);
	const shown = $derived(all ? plates : plates.slice(0, FIRST));
</script>

{#if plates.length}
	<section id="bookplates" class="plates mt-10 scroll-mt-24" aria-labelledby="bookplates-h">
		<h2 id="bookplates-h" class="section-heading">
			{t('bookplate.shelfTitle')} <span class="meta">· {plates.length}</span>
		</h2>
		{#if !name}
			<div class="mx-auto mb-6 max-w-md">
				<BookplateNameField />
			</div>
		{/if}
		<ul class="plate-grid">
			{#each shown as p (p.book.slug)}
				{@const style = plateStyle(p.book.author, p.book.slug)}
				{@const date = plateDate(p.at, locale)}
				<li class="flex flex-col items-center gap-2">
					<a class="plate-link" href={localizeHref(`/books/${p.book.slug}`)}>
						<Bookplate compact {name} title={p.book.title} author={p.book.author.name} {date} {style} lang={p.book.language} />
					</a>
					{#if name}
						<BookplateSave small slug={p.book.slug} {name} title={p.book.title} author={p.book.author.name} {date} {style} />
					{/if}
				</li>
			{/each}
		</ul>
		{#if plates.length > shown.length}
			<div class="mt-6 flex justify-center">
				<button type="button" class="btn btn-ghost" onclick={() => (all = true)}>
					{t('bios.showMore').replace('%n%', String(plates.length - shown.length))}
				</button>
			</div>
		{/if}
	</section>
{/if}

<style>
	.plates {
		padding: 1.25rem 1.25rem 1rem;
		border-radius: var(--radius-card);
		/* The Bookshelf's back wall, like the seals beside them. */
		background: var(--shelf-back);
	}
	.plate-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
		gap: 1.25rem 1rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.plate-link {
		display: block;
		width: 100%;
		color: inherit;
		text-decoration: none;
	}
	.plate-link:hover :global(.plate),
	.plate-link:focus-visible :global(.plate) {
		box-shadow: 0 0 0 2px var(--gold);
	}
</style>
