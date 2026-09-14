<script lang="ts">
	// A small "file a content-edit job" control, shared by the chapter title/text
	// fixes on the admin book page and the bio request on the authors worklist.
	// None of these edit anything live — a title, a chapter body and an author bio
	// are fixture-owned prose, so this files a content-edit job (a GitHub issue) a
	// worker turns into a fixture PR. The component is self-contained: it owns its
	// open/saving/error state and the filed result; the parent doesn't change when
	// a job is filed. The caller supplies `submit`, which returns the filed job, or
	// `null` when there's nothing to file (e.g. an unchanged title).
	interface Filed {
		url: string;
		number: number | null;
		created: boolean;
	}
	interface Props {
		/** Trigger label, e.g. "Fix title", "Flag text", "Request bio". */
		label: string;
		/** Files the job; `null` means "nothing to do" (just close the editor). */
		submit: (value: string) => Promise<{
			job: { url: string; number: number | null } | null;
			created: boolean;
		} | null>;
		/** Initial editor value (a title seeds from the current one). */
		seed?: string;
		/** Textarea instead of a one-line input — for a free-text note. */
		multiline?: boolean;
		placeholder?: string;
		/** Allow filing with an empty value (a bio note is optional). */
		allowEmpty?: boolean;
		/** Confirm-button label while editing, and the success label. */
		saveLabel?: string;
		filedLabel?: string;
		/** Accessible label for the editor field. */
		fieldLabel?: string;
	}
	let {
		label,
		submit,
		seed = '',
		multiline = false,
		placeholder = '',
		allowEmpty = false,
		saveLabel = 'Queue fix',
		filedLabel = 'fix queued',
		fieldLabel = label
	}: Props = $props();

	let editing = $state(false);
	// Seeded in open(), not here — a plain `$state(seed)` captures only the first
	// prop value (see the parent that re-renders rows).
	let draft = $state('');
	let saving = $state(false);
	let error = $state('');
	let filed = $state<Filed | null>(null);

	function open() {
		draft = seed;
		error = '';
		editing = true;
	}

	async function save() {
		const next = draft.trim();
		if (!next && !allowEmpty) {
			editing = false;
			return;
		}
		saving = true;
		error = '';
		try {
			const res = await submit(next);
			if (res === null) {
				editing = false; // nothing to file (e.g. an unchanged title)
				return;
			}
			filed = { url: res.job?.url ?? '', number: res.job?.number ?? null, created: res.created };
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
		>{filed.created ? filedLabel : 'already queued'} #{filed.number} ↗</a
	>
{:else if editing}
	<span class="flex flex-wrap items-center justify-end gap-1.5">
		{#if multiline}
			<!-- svelte-ignore a11y_autofocus -->
			<textarea
				bind:value={draft}
				autofocus
				{placeholder}
				aria-label={fieldLabel}
				rows="2"
				class="w-56 rounded border border-border bg-surface px-2 py-1 text-small text-text"
			></textarea>
		{:else}
			<!-- svelte-ignore a11y_autofocus -->
			<input
				bind:value={draft}
				autofocus
				{placeholder}
				onkeydown={(e) => e.key === 'Enter' && save()}
				aria-label={fieldLabel}
				class="w-48 rounded border border-border bg-surface px-2 py-0.5 text-small text-text"
			/>
		{/if}
		<button
			type="button"
			disabled={saving}
			onclick={save}
			class="text-small text-accent hover:underline disabled:opacity-50">{saving ? '…' : saveLabel}</button
		>
		<button type="button" onclick={() => (editing = false)} class="text-small text-muted hover:text-text"
			>Cancel</button
		>
		{#if error}<span class="w-full text-end text-micro text-warning">{error}</span>{/if}
	</span>
{:else}
	<button type="button" onclick={open} class="text-micro text-muted hover:text-accent">{label}</button>
{/if}
