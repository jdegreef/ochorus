<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { localizeHref } from '$lib/href';
	import { COLLECTION_MAX, inCollection, type Collection } from '$lib/journal';
	import { journal } from '$lib/journal.svelte';
	import { collectionFileName, collectionMarkdown, downloadFile } from '$lib/dataExport';

	/**
	 * An open collection's heading: its name and size, and what can be done with
	 * it as a whole — rename it, export it as a Markdown file, print it as a
	 * small book, or take it apart (the entries stay in the Notebook).
	 */
	let {
		collection,
		onrenamed,
		onclose
	}: {
		collection: Collection;
		/** The collection now goes by this name ('' when it was taken apart). */
		onrenamed: (name: string) => void;
		onclose: () => void;
	} = $props();

	const t = i18n.t;
	let renaming = $state(false);
	let newName = $state('');
	let confirmRemove = $state(false);
	let confirmTimer: ReturnType<typeof setTimeout>;

	function rename() {
		const to = newName.trim();
		if (!to) return;
		journal.renameCollection(collection.name, to);
		renaming = false;
		onrenamed(to);
	}

	function exportIt() {
		const entries = Object.values(journal.store).filter((e) => !e.deleted && inCollection(e, collection.name));
		const md = collectionMarkdown(collection.name, entries, new Date().toISOString());
		downloadFile(collectionFileName(collection.name), 'text/markdown;charset=utf-8', md);
	}

	// Two taps, like the other destructive settings: the first arms it for a few
	// seconds, the second takes the collection apart.
	function remove() {
		if (!confirmRemove) {
			confirmRemove = true;
			clearTimeout(confirmTimer);
			confirmTimer = setTimeout(() => (confirmRemove = false), 4000);
			return;
		}
		clearTimeout(confirmTimer);
		journal.renameCollection(collection.name, '');
		onrenamed('');
	}
</script>

<div class="head">
	<button class="chip" onclick={onclose}>← {t('notebook.allEntries')}</button>
	{#if renaming}
		<form
			class="flex grow flex-wrap items-center gap-2"
			onsubmit={(e) => {
				e.preventDefault();
				rename();
			}}
		>
			<!-- svelte-ignore a11y_autofocus -- opened by the reader's own tap -->
			<input
				class="field grow"
				bind:value={newName}
				maxlength={COLLECTION_MAX}
				aria-label={t('notebook.collectionLabel')}
				autofocus
			/>
			<button type="button" class="btn btn-ghost btn-sm" onclick={() => (renaming = false)}>{t('common.cancel')}</button>
			<button type="submit" class="btn btn-primary btn-sm" disabled={!newName.trim()}>{t('notebook.collectionRename')}</button>
		</form>
	{:else}
		<h2 class="name"><span aria-hidden="true">📁</span> {collection.name}</h2>
		<span class="count text-small"
			>{collection.count === 1 ? t('notebook.collectionOne') : m.notebook_collection_many({ n: String(collection.count) })}</span
		>
		<span class="actions">
			<button
				class="btn btn-ghost btn-sm"
				onclick={() => {
					newName = collection.name;
					renaming = true;
				}}>{t('notebook.collectionRename')}</button
			>
			<button class="btn btn-ghost btn-sm" onclick={exportIt}>{t('notebook.collectionExport')}</button>
			<a class="btn btn-ghost btn-sm" href={localizeHref(`/notebook/print?collection=${encodeURIComponent(collection.name)}`)}
				><span aria-hidden="true" class="me-1">🖨</span>{t('notebook.printLink')}</a
			>
			<button class="btn btn-ghost btn-sm remove" class:armed={confirmRemove} onclick={remove}>
				{confirmRemove ? t('notebook.collectionRemoveConfirm') : t('notebook.collectionRemove')}
			</button>
		</span>
	{/if}
</div>

<style>
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.9rem;
		margin: 1.5rem 0 1.25rem;
		padding-bottom: 0.6rem;
		border-bottom: 2px solid var(--border);
	}
	.name {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.15rem;
		margin-inline-start: auto;
	}
	.remove.armed {
		color: var(--danger);
	}
</style>
