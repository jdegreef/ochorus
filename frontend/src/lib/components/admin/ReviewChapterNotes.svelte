<!--
	Reviewers' notes on the chapter open in the review queue's side-by-side
	(backend `AdminReviewNotesView`, model `ReviewNote`). Advisory — they gate
	nothing — so a second reviewer, or the next session, picks up where the
	first stopped. Loads the translation's notes once; shows this chapter's, and
	says which other chapters carry some.
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import {
		addReviewNote,
		deleteReviewNote,
		getReviewNotes,
		REVIEW_NOTE_MAX,
		type ReviewNote,
		type ReviewTarget
	} from '$lib/library-admin';

	let {
		target,
		chapter,
		onpick
	}: {
		target: ReviewTarget;
		/** The chapter on screen (its `order`; 0 for a single-body work). */
		chapter: number;
		/** Open another chapter (from "also noted on chapter …"). */
		onpick?: (chapter: number) => void;
	} = $props();

	let notes = $state<ReviewNote[]>([]);
	let error = $state('');
	let draft = $state('');
	let saving = $state(false);

	// Reload when the translation changes (the panel is reused across rows) —
	// keyed on the string, not the prop object, which the parent rebuilds on
	// every render.
	const targetKey = $derived(`${target.kind}:${target.slug}:${target.language}`);
	$effect(() => {
		void targetKey;
		let stale = false;
		error = '';
		untrack(() => getReviewNotes(target))
			.then((r) => {
				if (!stale) notes = r.notes;
			})
			.catch((e) => {
				if (!stale) error = e instanceof Error ? e.message : 'Could not load notes.';
			});
		return () => {
			stale = true;
		};
	});

	const here = $derived(notes.filter((n) => n.chapter === chapter));
	const elsewhere = $derived(
		[...new Set(notes.filter((n) => n.chapter !== chapter).map((n) => n.chapter))].sort(
			(a, b) => a - b
		)
	);
	const when = (iso: string) =>
		new Date(iso).toLocaleDateString('en', { month: 'short', day: 'numeric' });

	async function add() {
		const note = draft.trim();
		if (!note) return;
		saving = true;
		error = '';
		try {
			notes = [...notes, await addReviewNote({ ...target, chapter, note })];
			draft = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save the note.';
		} finally {
			saving = false;
		}
	}

	async function remove(n: ReviewNote) {
		error = '';
		try {
			await deleteReviewNote(n);
			notes = notes.filter((x) => x.id !== n.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not remove the note.';
		}
	}
</script>

<div class="mb-3 rounded-sm border border-border bg-bg p-3">
	<p class="text-small mb-2 font-semibold">
		Reviewer notes{#if chapter}{' '}<span class="font-normal text-muted">
				· chapter {chapter}
			</span>{/if}
	</p>
	{#if here.length}
		<ul class="mb-2 space-y-2">
			{#each here as n (n.id)}
				<li class="text-small border-t border-border pt-2 first:border-0 first:pt-0">
					<p class="whitespace-pre-line text-text">{n.note}</p>
					<p class="text-micro text-muted">
						{n.author || 'someone'} · {when(n.created_at)}
						{#if n.mine}
							· <button type="button" class="hover:text-danger" onclick={() => remove(n)}>
								remove
							</button>
						{/if}
					</p>
				</li>
			{/each}
		</ul>
	{/if}
	{#if elsewhere.length}
		<p class="text-micro mb-2 text-muted">
			Also noted on chapter{elsewhere.length === 1 ? '' : 's'}
			{#each elsewhere as c, i (c)}{#if i},
				{/if}{#if onpick}<button
						type="button"
						class="text-accent hover:underline"
						onclick={() => onpick(c)}
					>
						{c}
					</button>{:else}{c}{/if}{/each}.
		</p>
	{/if}
	<label class="sr-only" for="review-note-{targetKey}">Add a note on this chapter</label>
	<textarea
		id="review-note-{targetKey}"
		rows="2"
		maxlength={REVIEW_NOTE_MAX}
		placeholder="What should the next reviewer know about this chapter?"
		class="text-small w-full rounded-sm border border-border bg-surface px-2 py-1.5"
		bind:value={draft}></textarea>
	<div class="mt-1 flex items-center gap-2">
		<button
			type="button"
			class="btn btn-sm btn-ghost"
			disabled={saving || !draft.trim()}
			aria-busy={saving ? 'true' : undefined}
			onclick={add}
		>
			{#if saving}<span class="btn-spinner" aria-hidden="true"></span>{/if}Add note
		</button>
		{#if error}<span class="text-small text-warning">{error}</span>{/if}
	</div>
</div>
