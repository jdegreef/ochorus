<script lang="ts">
	/**
	 * "Insert tag": drops a merge tag such as `{first_name}` into whichever text
	 * field was focused last (`getTarget`), at the cursor. The field's own input
	 * event carries the change, so its binding updates as if it had been typed.
	 */
	import { getMergeTags, type MergeTag } from '$lib/library-admin';

	let {
		getTarget,
		disabled = false
	}: { getTarget: () => HTMLInputElement | HTMLTextAreaElement | null; disabled?: boolean } = $props();

	let open = $state(false);
	let tags = $state<MergeTag[]>([]);
	let hint = $state('');

	async function toggle() {
		open = !open;
		if (open && !tags.length) {
			try {
				tags = (await getMergeTags()).tags;
			} catch {
				hint = "Couldn't load the tags.";
			}
		}
	}

	function insert(tag: MergeTag) {
		const el = getTarget();
		if (!el || !el.isConnected) {
			hint = 'Click into a subject, heading, text or label first, then choose a tag.';
			return;
		}
		const token = `{${tag.key}}`;
		const start = el.selectionStart ?? el.value.length;
		const end = el.selectionEnd ?? start;
		el.setRangeText(token, start, end, 'end');
		el.dispatchEvent(new Event('input', { bubbles: true }));
		el.focus();
		hint = '';
		open = false;
	}
</script>

<div class="relative inline-block">
	<button
		class="btn btn-ghost btn-sm"
		aria-expanded={open}
		aria-haspopup="true"
		onmousedown={(e) => e.preventDefault()}
		onclick={toggle}
		{disabled}>{'{ }'} Insert tag ▾</button
	>
	{#if open}
		<div class="absolute left-0 top-full z-(--z-popover) mt-1 w-80 rounded-card border border-border bg-surface p-2 shadow-lg" role="menu">
			{#each tags as tag (tag.key)}
				<button
					class="flex w-full items-baseline justify-between gap-3 rounded-md p-2 text-start hover:bg-surface-2"
					role="menuitem"
					title={tag.description}
					onmousedown={(e) => e.preventDefault()}
					onclick={() => insert(tag)}
				>
					<span class="text-small font-semibold text-text">{tag.label}</span>
					<span class="truncate text-micro text-muted">{tag.sample}</span>
				</button>
			{/each}
			<p class="mt-1 border-t border-border px-2 pt-2 text-micro text-muted">
				No value for a reader? Add a fallback after a bar — <code>{'{last_book|a classic}'}</code> — or the sentence with
				the tag is left out of their email.
			</p>
		</div>
	{/if}
	{#if hint}<p class="mt-1 text-micro text-warning" aria-live="polite">{hint}</p>{/if}
</div>
