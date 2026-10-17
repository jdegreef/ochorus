<script lang="ts">
	/**
	 * Start an email from a template: the starters shipped with the site and the
	 * team's own saved ones, as a gallery of real thumbnails, filtered by kind or
	 * searched by name. "Use" copies the design into a new draft; editing a
	 * template never changes broadcasts already made from it.
	 */
	import EmailPreview from '$lib/components/EmailPreview.svelte';
	import EmailThumbnail from '$lib/components/EmailThumbnail.svelte';
	import type {
		EmailTemplate,
		EmailTemplateBase,
		EmailTemplates,
		TemplateCategory
	} from '$lib/library-admin';

	let {
		data,
		busy = false,
		onUse,
		onBlank,
		onEdit,
		onDelete
	}: {
		data: EmailTemplates;
		busy?: boolean;
		onUse: (t: EmailTemplateBase) => void;
		onBlank: () => void;
		onEdit: (t: EmailTemplate) => void;
		onDelete: (t: EmailTemplate) => void;
	} = $props();

	type Card = EmailTemplateBase & { saved?: EmailTemplate; id: string };

	let filter = $state<TemplateCategory | 'all' | 'saved'>('all');
	let query = $state('');
	let previewing = $state<Card | null>(null);

	const cards = $derived<Card[]>([
		...data.templates.map((t) => ({ ...t, saved: t, id: `saved:${t.id}` })),
		...data.starters.map((t) => ({ ...t, id: `starter:${t.key}` }))
	]);
	const shown = $derived(
		cards.filter((c) => {
			if (filter === 'saved' ? !c.saved : filter !== 'all' && c.category !== filter) return false;
			const q = query.trim().toLowerCase();
			return !q || `${c.name} ${c.description}`.toLowerCase().includes(q);
		})
	);
	const categoryLabel = (key: TemplateCategory) =>
		data.categories.find((c) => c.key === key)?.label ?? key;
	const firstLocale = (c: Card) => (c.locales.includes('en') ? 'en' : (c.locales[0] ?? 'en'));
</script>

<section class="mb-5" aria-labelledby="gallery-title">
	<div class="mb-3 flex flex-wrap items-end justify-between gap-3">
		<div>
			<h2 id="gallery-title" class="text-h3">Start from a template</h2>
			<p class="text-small text-muted">Every template is made of the same blocks as the designer, so nothing is locked.</p>
		</div>
		<div class="flex flex-wrap gap-2">
			<input
				class="rounded-md border border-border bg-surface p-2 text-small"
				type="search"
				aria-label="Search templates"
				placeholder="Search templates"
				bind:value={query}
			/>
			<button class="btn btn-primary btn-sm" onclick={onBlank} disabled={busy}>Blank email</button>
		</div>
	</div>

	<div class="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Filter templates">
		{#each [{ key: 'all', label: 'All' }, ...data.categories, { key: 'saved', label: `Saved by your team · ${data.templates.length}` }] as f (f.key)}
			<button
				class="rounded-full border px-3 py-1 text-micro {filter === f.key ? 'border-accent bg-accent text-accent-contrast' : 'border-border text-text hover:border-accent'}"
				aria-pressed={filter === f.key}
				onclick={() => (filter = f.key as typeof filter)}
			>{f.label}</button>
		{/each}
	</div>

	{#if shown.length === 0}
		<p class="rounded-card border border-border bg-surface p-6 text-center text-small text-muted">No template matches.</p>
	{:else}
		<ul class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
			{#each shown as c (c.id)}
				<li class="flex flex-col overflow-hidden rounded-card border border-border bg-surface">
					<EmailThumbnail locale={firstLocale(c)} subject={c.subject[firstLocale(c)] ?? ''} content={c.content[firstLocale(c)]} />
					<div class="flex flex-1 flex-col gap-1 p-3">
						<div class="flex items-baseline justify-between gap-2">
							<h3 class="text-small font-semibold text-text">{c.name}</h3>
							<span class="shrink-0 text-micro text-muted">{c.saved ? 'Saved' : categoryLabel(c.category)}</span>
						</div>
						{#if c.description}<p class="flex-1 text-micro text-muted">{c.description}</p>{/if}
						<p class="text-micro text-muted">{c.locales.join(', ')}{c.saved?.created_by ? ` · ${c.saved.created_by}` : ''}</p>
						<div class="mt-2 flex flex-wrap gap-1">
							<button class="btn btn-primary btn-sm" onclick={() => onUse(c)} disabled={busy}>Use</button>
							<button class="btn btn-ghost btn-sm" onclick={() => (previewing = c)}>Preview</button>
							{#if c.saved}
								<button class="btn btn-ghost btn-sm" onclick={() => onEdit(c.saved!)} disabled={busy}>Edit</button>
								<button class="btn btn-ghost btn-sm text-danger" onclick={() => onDelete(c.saved!)} disabled={busy}>Delete</button>
							{/if}
						</div>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</section>

{#if previewing}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation" onclick={(e) => e.target === e.currentTarget && (previewing = null)}>
		<div class="max-h-full w-full max-w-3xl overflow-y-auto rounded-card bg-surface p-4" role="dialog" aria-modal="true" aria-label="Preview of {previewing.name}">
			<div class="mb-3 flex items-center justify-between gap-2">
				<h3 class="text-h3">{previewing.name}</h3>
				<div class="flex gap-2">
					<button class="btn btn-primary btn-sm" onclick={() => { const t = previewing!; previewing = null; onUse(t); }} disabled={busy}>Use this template</button>
					<button class="btn btn-ghost btn-sm" onclick={() => (previewing = null)}>Close</button>
				</div>
			</div>
			<EmailPreview
				locale={firstLocale(previewing)}
				subject={previewing.subject[firstLocale(previewing)] ?? ''}
				content={previewing.content[firstLocale(previewing)]}
			/>
		</div>
	</div>
{/if}
