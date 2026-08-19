<script lang="ts">
	/**
	 * A language's translation settings: the Bible its scripture is quoted from
	 * and the glossary its theology is worded with.
	 *
	 * Shown for every language, editable only for those the admin created. The
	 * built-in ones are defined in backend/library/language_seed.py and
	 * re-asserted on every deploy, so an edit here would appear to work and
	 * revert the next time we ship — the API refuses it, and this says why
	 * rather than offering a control that lies.
	 */
	import { updateAdminLanguageSettings, type LanguageSettings } from '$lib/library-admin';

	let {
		settings,
		onsaved
	}: { settings: LanguageSettings; onsaved?: (next: LanguageSettings) => void } = $props();

	let editing = $state(false);
	let saving = $state(false);
	let error = $state('');
	let note = $state('');

	// Edit buffers, filled from `settings` when editing starts rather than at
	// init: a save reloads the page's data, and stale buffers would win.
	let bibleCode = $state('');
	let bibleLabel = $state('');
	let bibleLicence = $state('');
	let bibleAttribution = $state('');
	let glossary = $state<Record<string, string>>({});

	const missing = $derived(settings.glossary_terms.filter((t) => !(glossary[t] ?? '').trim()));

	function startEditing() {
		bibleCode = settings.bible_code;
		bibleLabel = settings.bible_label;
		bibleLicence = settings.bible_licence;
		bibleAttribution = settings.bible_attribution;
		glossary = { ...settings.glossary };
		error = '';
		note = '';
		editing = true;
	}

	async function save() {
		saving = true;
		error = '';
		try {
			const res = await updateAdminLanguageSettings(settings.code, {
				bible_code: bibleCode.trim(),
				bible_label: bibleLabel.trim(),
				bible_licence: bibleLicence.trim(),
				bible_attribution: bibleAttribution.trim(),
				glossary
			});
			note = res.bible_verified ? '' : res.bible_note;
			onsaved?.(res.settings);
			editing = false;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			saving = false;
		}
	}
</script>

<section class="mb-6 rounded-2xl border border-border bg-surface p-5">
	<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-h3">Translation settings</h2>
		{#if settings.repo_managed}
			<span class="text-small text-muted">Defined in the repo</span>
		{:else if !editing}
			<button class="text-small font-semibold text-accent hover:underline" onclick={startEditing}>
				Edit
			</button>
		{/if}
	</div>

	{#if !editing}
		<dl class="space-y-1.5 text-body">
			<div class="flex gap-2">
				<dt class="w-32 flex-none text-muted">Bible</dt>
				<dd>{settings.bible_label || settings.bible_code || '—'} <span class="text-small text-muted">({settings.bible_code || 'none'})</span></dd>
			</div>
			{#if settings.bible_licence}
				<!-- Shown only when the licence asks for something. A "Licence: public
				     domain" row on every other language would be noise, and the whole
				     point of this row is that it stands out on the one language where
				     going live incurs an obligation. -->
				<div class="flex gap-2">
					<dt class="w-32 flex-none text-muted">Licence</dt>
					<dd class={settings.bible_attribution.trim() ? '' : 'text-warning'}>
						{settings.bible_licence} —
						{#if settings.bible_attribution.trim()}
							credited
						{:else}
							no credit line, so this language cannot go live
						{/if}
					</dd>
				</div>
			{/if}
			<div class="flex gap-2">
				<dt class="w-32 flex-none text-muted">Glossary</dt>
				<dd class={settings.missing_glossary_terms.length ? 'text-warning' : ''}>
					{#if settings.missing_glossary_terms.length}
						{settings.missing_glossary_terms.length} of {settings.glossary_terms.length} terms
						missing: {settings.missing_glossary_terms.join(', ')}
					{:else}
						All {settings.glossary_terms.length} terms defined
					{/if}
				</dd>
			</div>
			<div class="flex gap-2">
				<dt class="w-32 flex-none text-muted">Direction</dt>
				<dd>{settings.rtl ? 'Right-to-left' : 'Left-to-right'}</dd>
			</div>
		</dl>
		{#if settings.repo_managed}
			<p class="mt-3 text-small text-muted">
				This language's identity is re-seeded from
				<code>backend/library/language_seed.py</code> on every deploy, so it is edited
				there rather than here.
			</p>
		{/if}
		{#if note}
			<p class="mt-3 text-small text-warning">{note}</p>
		{/if}
	{:else}
		<div class="space-y-4">
			<div class="flex flex-wrap gap-4">
				<label class="text-small">
					<span class="mb-1 block text-muted">Take Root code</span>
					<input
						class="field w-40"
						bind:value={bibleCode}
					/>
				</label>
				<label class="text-small">
					<span class="mb-1 block text-muted">Bible label</span>
					<input
						class="field w-64"
						bind:value={bibleLabel}
					/>
				</label>
				<label class="text-small">
					<span class="mb-1 block text-muted">Licence (blank = public domain)</span>
					<input
						class="field w-48"
						bind:value={bibleLicence}
						placeholder="CC BY-SA 4.0"
					/>
				</label>
			</div>

			{#if bibleLicence.trim()}
				<!-- Appears the moment a licence is typed, because that is the moment
				     the obligation exists. Naming bibleCredit.ts here is deliberate:
				     the reader is a prerendered static site, so a credit that lives
				     only in this row is a credit no reader will ever see. -->
				<label class="block text-small">
					<span class="mb-1 block text-muted">Credit line shown to readers</span>
					<input
						class="field w-full"
						bind:value={bibleAttribution}
						placeholder="Scripture quotations are from ..."
					/>
					<span class="mt-1 block text-muted">
						Add the same text to <code>frontend/src/lib/bibleCredit.ts</code> — that is
						what renders it in the footer. Readiness blocks the launch while this is
						empty.
					</span>
				</label>
			{/if}

			<div class="border-t border-border pt-4">
				<p class="mb-3 text-small text-muted">
					Every term is required — a partial glossary lets the translator word the same
					doctrine differently in each chapter, and nothing about the output looks wrong.
				</p>
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each settings.glossary_terms as term (term)}
						<label class="text-small">
							<span class="mb-1 block text-muted">{term}</span>
							<input
								class="field w-full"
								bind:value={glossary[term]}
							/>
						</label>
					{/each}
				</div>
			</div>

			{#if error}
				<p class="text-small text-warning">{error}</p>
			{/if}

			<div class="flex items-center gap-3">
				<button
					class="rounded-full bg-accent px-4 py-1.5 text-small font-semibold text-accent-contrast disabled:opacity-50"
					disabled={saving || missing.length > 0 || !bibleCode.trim()}
					onclick={save}
				>
					{saving ? 'Saving…' : 'Save'}
				</button>
				<button class="text-small text-muted hover:text-text" onclick={() => (editing = false)}>
					Cancel
				</button>
				{#if missing.length}
					<span class="text-small text-muted">{missing.length} term(s) still to fill in.</span>
				{/if}
			</div>
		</div>
	{/if}
</section>
