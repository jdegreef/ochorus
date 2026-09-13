<script lang="ts">
	// A "Fix title" control for one chapter on the admin book page. A chapter
	// title is fixture-owned prose, so this doesn't edit anything live — it files
	// a content-edit job (a GitHub issue) a worker turns into a fixture PR. The
	// component is self-contained: it owns its edit/saving/error state and the
	// filed result; nothing in the parent changes when a job is filed.
	import { fileRetitleJob } from '$lib/library-admin';

	interface Props {
		slug: string;
		language: string;
		order: number;
		title: string;
	}
	let { slug, language, order, title }: Props = $props();

	let editing = $state(false);
	// Seeded from `title` when the editor opens (see open()), not here — a plain
	// `$state(title)` would only ever capture the prop's first value.
	let draft = $state('');
	let saving = $state(false);
	let error = $state('');
	let filed = $state<{ url: string; number: number | null; created: boolean } | null>(null);

	function open() {
		draft = title;
		error = '';
		editing = true;
	}

	async function save() {
		const next = draft.trim();
		if (!next || next === title.trim()) {
			editing = false;
			return;
		}
		saving = true;
		error = '';
		try {
			const res = await fileRetitleJob(slug, language, order, next);
			filed = {
				url: res.job?.url ?? '',
				number: res.job?.number ?? null,
				created: res.created
			};
			editing = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not file the fix.';
		} finally {
			saving = false;
		}
	}
</script>

{#if filed}
	<a href={filed.url} target="_blank" rel="noopener" class="text-micro text-accent hover:underline"
		>{filed.created ? 'fix queued' : 'already queued'} #{filed.number} ↗</a
	>
{:else if editing}
	<span class="flex flex-wrap items-center justify-end gap-1.5">
		<!-- svelte-ignore a11y_autofocus -->
		<input
			bind:value={draft}
			autofocus
			onkeydown={(e) => e.key === 'Enter' && save()}
			aria-label="New chapter title"
			class="w-48 rounded border border-border bg-surface px-2 py-0.5 text-small text-text"
		/>
		<button type="button" disabled={saving} onclick={save} class="text-small text-accent hover:underline disabled:opacity-50">{saving ? '…' : 'Queue fix'}</button>
		<button type="button" onclick={() => (editing = false)} class="text-small text-muted hover:text-text">Cancel</button>
		{#if error}<span class="w-full text-end text-micro text-warning">{error}</span>{/if}
	</span>
{:else}
	<button type="button" onclick={open} class="text-micro text-muted hover:text-accent">Fix title</button>
{/if}
