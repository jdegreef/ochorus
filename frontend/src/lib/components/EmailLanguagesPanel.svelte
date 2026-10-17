<script lang="ts">
	/**
	 * One email, every language: where each language of a broadcast stands —
	 * written, drafted by AI and waiting for review, approved, or missing — how
	 * many readers in the audience get it, and which of its library items have no
	 * edition there. "Translate the missing" asks for every AI draft at once;
	 * nothing AI-written goes out until it is approved. Review state is admin-only.
	 */
	import type { LanguageRow, LanguagesOverview, LanguageStatus } from '$lib/library-admin';

	let {
		overview,
		busy = false,
		readOnly = false,
		onRequestAll,
		onFetchAll,
		onRequest,
		onReview,
		onOpen,
		onStrict
	}: {
		overview: LanguagesOverview;
		busy?: boolean;
		readOnly?: boolean;
		onRequestAll: () => void;
		onFetchAll: () => void;
		onRequest: (code: string) => void;
		onReview: (code: string) => void;
		onOpen: (code: string) => void;
		onStrict: (strict: boolean) => void;
	} = $props();

	const STATUS: Record<LanguageStatus, { label: string; cls: string }> = {
		source: { label: 'Source', cls: 'bg-accent-soft text-accent' },
		approved: { label: 'Approved', cls: 'bg-accent-soft text-accent' },
		written: { label: 'Written', cls: 'bg-accent-soft text-accent' },
		draft: { label: 'Needs review', cls: 'bg-warning/15 text-warning' },
		requested: { label: 'AI draft requested', cls: 'bg-surface-2 text-muted' },
		incomplete: { label: 'Incomplete', cls: 'bg-warning/15 text-warning' },
		missing: { label: 'Not translated', cls: 'bg-surface-2 text-muted' }
	};

	const ready = $derived(overview.rows.filter((r) => r.sendable));
	const waiting = $derived(overview.rows.filter((r) => r.status === 'requested').length);
	const unready = $derived(overview.rows.filter((r) => !r.sendable && r.readers > 0));
	const unreadyReaders = $derived(unready.reduce((n, r) => n + r.readers, 0));
	const gapText = (r: LanguageRow) =>
		r.gaps.length ? `${r.gaps.length} item${r.gaps.length === 1 ? '' : 's'} not in ${r.name} — left out` : 'Everything is available';
</script>

<section class="mb-5 rounded-card border border-border bg-surface p-4" aria-labelledby="languages-title">
	<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
		<div>
			<h2 id="languages-title" class="text-h3">Languages</h2>
			<p class="text-small text-muted">
				{ready.length} of {overview.rows.length} ready to send. Write once, ask for AI drafts of the rest, and approve
				each one — nothing AI-written goes out unapproved.
			</p>
		</div>
		{#if !readOnly}
			<div class="flex flex-wrap gap-2">
				{#if waiting}
					<button class="btn btn-ghost btn-sm" onclick={onFetchAll} disabled={busy}>Check for {waiting} draft{waiting === 1 ? '' : 's'}</button>
				{/if}
				{#if overview.missing.length && overview.source}
					<button class="btn btn-primary btn-sm" onclick={onRequestAll} disabled={busy}>Translate the {overview.missing.length} missing</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class="overflow-x-auto">
		<table class="w-full text-small">
			<thead>
				<tr class="border-b border-border text-start text-muted">
					<th class="p-2 font-semibold">Language</th>
					<th class="p-2 font-semibold">Status</th>
					<th class="p-2 text-end font-semibold">Readers</th>
					<th class="p-2 font-semibold">Library check</th>
					<th class="p-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each overview.rows as r (r.code)}
					<tr class="border-b border-border/50">
						<td class="p-2"><span class="font-semibold text-text">{r.native_name}</span> <span class="text-muted">{r.code}</span></td>
						<td class="p-2">
							<span class="rounded-full px-2 py-0.5 text-micro {STATUS[r.status].cls}">{STATUS[r.status].label}</span>
							{#if r.stale}<span class="ms-1 text-micro text-warning" title="The source changed after this translation was made">source changed</span>{/if}
						</td>
						<td class="p-2 text-end tabular-nums">{r.readers}</td>
						<td class="p-2 {r.gaps.length ? 'text-warning' : 'text-muted'}" title={r.gaps.map((g) => `${g.type}: ${g.slug}`).join('\n')}>{gapText(r)}</td>
						<td class="p-2 text-end whitespace-nowrap">
							{#if r.status === 'draft'}
								<button class="btn btn-primary btn-sm" onclick={() => onReview(r.code)} disabled={busy}>Review</button>
							{:else if r.status === 'missing' && !readOnly && overview.source}
								<button class="btn btn-ghost btn-sm" onclick={() => onRequest(r.code)} disabled={busy}>Translate</button>
							{:else if r.status === 'requested' && r.issue_url}
								<a class="btn btn-ghost btn-sm" href={r.issue_url} target="_blank" rel="noopener">Job</a>
							{:else if r.status !== 'missing'}
								<button class="btn btn-ghost btn-sm" onclick={() => onOpen(r.code)}>Open</button>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<fieldset class="mt-3 text-small" disabled={readOnly || busy}>
		<legend class="mb-1 font-semibold text-text">
			Readers whose language isn’t ready{unreadyReaders ? ` (${unreadyReaders} in this audience)` : ''}
		</legend>
		<label class="flex items-center gap-2">
			<input type="radio" name="strict" checked={!overview.strict_locale} onchange={() => onStrict(false)} />
			get the English version (or the first ready language)
		</label>
		<label class="flex items-center gap-2">
			<input type="radio" name="strict" checked={overview.strict_locale} onchange={() => onStrict(true)} />
			don’t get this email
		</label>
	</fieldset>
</section>
