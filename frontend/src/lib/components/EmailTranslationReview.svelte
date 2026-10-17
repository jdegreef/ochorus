<script lang="ts">
	/**
	 * Review an AI draft beside its source, piece by piece: the source's words on
	 * the left, the draft's on the right to edit in place, then approve. A draft is
	 * made from the source's own blocks, so the two line up block for block; if an
	 * admin has since reshaped either, the pieces that no longer line up say so
	 * and are edited in the designer instead.
	 */
	import type { BroadcastBlock, EmailBlock } from '$lib/library-admin';

	let {
		sourceName,
		targetName,
		sourceSubject,
		source,
		subject = $bindable(),
		target = $bindable(),
		busy = false,
		onApprove,
		onClose
	}: {
		sourceName: string;
		targetName: string;
		sourceSubject: string;
		source: BroadcastBlock;
		subject: string;
		target: BroadcastBlock;
		busy?: boolean;
		onApprove: () => void;
		onClose: () => void;
	} = $props();

	/** The fields that carry words (backend `blocks.WORD_FIELDS`). */
	const WORDS = ['text', 'label', 'attribution', 'heading', 'title', 'eyebrow', 'caption', 'alt', 'reference'] as const;
	type Word = (typeof WORDS)[number];
	const read = (b: EmailBlock | undefined, f: Word) => ((b as Record<string, unknown> | undefined)?.[f] as string | undefined) ?? '';

	const pieces = $derived(
		source.blocks.flatMap((b, i) =>
			WORDS.filter((f) => read(b, f)).map((f) => ({ i, f, type: b.type, lines: target.blocks[i]?.type === b.type }))
		)
	);
	const shapeDiffers = $derived(source.blocks.length !== target.blocks.length);

	function write(i: number, f: Word, value: string) {
		target.blocks[i] = { ...target.blocks[i], [f]: value } as EmailBlock;
	}
</script>

<section class="mb-5 rounded-card border border-warning/40 bg-surface p-4" aria-labelledby="review-title">
	<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
		<h2 id="review-title" class="text-h3">Review · {targetName}</h2>
		<div class="flex gap-2">
			<button class="btn btn-ghost btn-sm" onclick={onClose}>Back to the designer</button>
			<button class="btn btn-primary btn-sm" onclick={onApprove} disabled={busy}>Approve {targetName}</button>
		</div>
	</div>
	<p class="mb-3 text-small text-muted">
		An AI draft. Read each piece against the {sourceName}, edit anything that’s off, then approve it — it can’t be sent
		until you do.
	</p>
	{#if shapeDiffers}
		<p class="mb-3 rounded-md bg-warning/10 p-2 text-small text-warning">
			The two versions no longer have the same blocks, so some pieces may not line up — check those in the designer.
		</p>
	{/if}

	<div class="grid grid-cols-1 gap-x-4 gap-y-2 text-small md:grid-cols-2">
		<div class="hidden text-micro font-semibold uppercase text-muted md:block">{sourceName}</div>
		<div class="hidden text-micro font-semibold uppercase text-muted md:block">{targetName} — edit in place</div>

		<div class="rounded-md bg-surface-2 p-2"><span class="text-micro text-muted">Subject ·</span>{" "}{sourceSubject}</div>
		<input class="rounded-md border border-border bg-surface p-2" aria-label="{targetName} subject" bind:value={subject} />

		{#if source.preheader}
			<div class="rounded-md bg-surface-2 p-2"><span class="text-micro text-muted">Inbox text ·</span>{" "}{source.preheader}</div>
			<input class="rounded-md border border-border bg-surface p-2" aria-label="{targetName} inbox text" bind:value={target.preheader} />
		{/if}

		{#each pieces as p (`${p.i}:${p.f}`)}
			<div class="whitespace-pre-line rounded-md bg-surface-2 p-2"><span class="text-micro text-muted">{p.type} · {p.f} ·</span>{" "}{read(source.blocks[p.i], p.f)}</div>
			{#if p.lines}
				<textarea
					class="min-h-[2.75rem] rounded-md border border-border bg-surface p-2"
					aria-label="{targetName} {p.type} {p.f}"
					rows={Math.min(8, Math.max(1, Math.ceil(read(source.blocks[p.i], p.f).length / 60)))}
					value={read(target.blocks[p.i], p.f)}
					oninput={(e) => write(p.i, p.f, (e.currentTarget as HTMLTextAreaElement).value)}
				></textarea>
			{:else}
				<p class="rounded-md bg-warning/10 p-2 text-warning">This block differs in the {targetName} version — edit it in the designer.</p>
			{/if}
		{/each}
	</div>
</section>
