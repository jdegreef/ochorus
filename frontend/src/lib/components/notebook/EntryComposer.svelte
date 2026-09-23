<script lang="ts">
	import { tick } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { applyFormat } from '$lib/richText';
	import {
		BODY_MAX,
		PERSON_MAX,
		PRAYER_GROUPS,
		REF_MAX,
		TITLE_MAX,
		COLLECTION_MAX,
		collectionsOf,
		knownPeople,
		type JournalKind,
		type PrayerGroup
	} from '$lib/journal';
	import { journal, type EntryDraft } from '$lib/journal.svelte';
	import { appendPhrase } from '$lib/dictation.svelte';
	import DictateButton from './DictateButton.svelte';

	/**
	 * Writing on the Notebook's page — a new note or prayer, or an edit of one.
	 *
	 * The body is a ruled textarea whose line-height IS the rule spacing, so the
	 * words sit on the lines like a real notebook's. Ctrl/⌘+Enter saves, Escape
	 * cancels an edit.
	 */
	let {
		initial,
		kind: startKind = 'note',
		editing = false,
		defaults = {},
		placeholder: placeholderOverride,
		onsave,
		oncancel
	}: {
		/** An entry being edited — or, for a new one, a prefill ("a prayer for Anna"). */
		initial?: Partial<EntryDraft>;
		/** Which kind a NEW entry starts as (the open tab decides). */
		kind?: JournalKind;
		editing?: boolean;
		/**
		 * What a NEW entry starts with unless the reader changes it — the open
		 * collection; a reflection's title and collection. Unlike `initial`, this
		 * does not open the composer by itself.
		 */
		defaults?: Partial<EntryDraft>;
		/** The line that invites writing, when the caller has a better one (a
		 *  reflection's prompt) than "Write a note…". */
		placeholder?: string;
		onsave: (draft: EntryDraft) => void;
		oncancel?: () => void;
	} = $props();

	const t = i18n.t;

	// Seeded once from the props: this is a form's own working copy, and an
	// edit form is re-mounted per entry, so it must not track later prop changes.
	const seed = (() => ({
		draft: {
			kind: startKind,
			title: '',
			body: '',
			ref: '',
			person: '',
			group: '' as PrayerGroup | '',
			collection: '',
			...defaults,
			...initial
		},
		// A new entry opens as one line and unfolds when the reader starts writing
		// — unless it arrives prefilled, which means they already asked to write.
		open: editing || !!initial
	}))();
	let kind = $state<JournalKind>(seed.draft.kind);
	let title = $state(seed.draft.title);
	let body = $state(seed.draft.body);
	let ref = $state(seed.draft.ref);
	let person = $state(seed.draft.person);
	let group = $state<PrayerGroup | ''>(seed.draft.group);
	let collection = $state(seed.draft.collection);
	// The reader's collections, most recent first, to file this under in a tap.
	const collectionNames = $derived(collectionsOf(journal.store).map((c) => c.name));
	const collectionListId = `collections-${Math.random().toString(36).slice(2, 8)}`;
	let open = $state(seed.open);

	// Everyone already prayed for, so "Anna" is typed once and picked after.
	const people = $derived(knownPeople(journal.store));
	const listId = `people-${Math.random().toString(36).slice(2, 8)}`;

	/** Back to a fresh entry — with the caller's defaults, not blanks. */
	function reset() {
		title = defaults.title ?? '';
		body = '';
		ref = defaults.ref ?? '';
		person = defaults.person ?? '';
		group = defaults.group ?? '';
		collection = defaults.collection ?? '';
		open = false;
	}

	const canSave = $derived(body.trim().length > 0 || title.trim().length > 0);

	function save() {
		if (!canSave) return;
		onsave({ kind, title, body, ref, person, group, collection });
		if (!editing) reset();
	}

	let sheet = $state<HTMLTextAreaElement>();

	/** Bold, italic, a list or a quotation — on the selection, or the line the
	 *  cursor is on (see applyFormat). */
	async function format(kind: 'bold' | 'italic' | 'list' | 'quote') {
		if (!sheet) return;
		const r = applyFormat(body, sheet.selectionStart, sheet.selectionEnd, kind);
		body = r.text;
		await tick();
		sheet.focus();
		// Bold and italic keep the words selected (tap again to undo). A list or
		// quotation leaves the cursor at the end of the line, ready to carry on —
		// a selected line would be replaced by the next keystroke.
		if (kind === 'list' || kind === 'quote') sheet.setSelectionRange(r.end, r.end);
		else sheet.setSelectionRange(r.start, r.end);
	}

	function onkeydown(e: KeyboardEvent) {
		const mod = e.metaKey || e.ctrlKey;
		if (mod && e.target === sheet && (e.key === 'b' || e.key === 'i')) {
			e.preventDefault();
			void format(e.key === 'b' ? 'bold' : 'italic');
		} else if (e.key === 'Enter' && mod) {
			e.preventDefault();
			save();
		} else if (e.key === 'Escape' && oncancel) {
			oncancel();
		}
	}

	const placeholder = $derived(
		placeholderOverride ?? (kind === 'prayer' ? t('notebook.prayerPlaceholder') : t('notebook.notePlaceholder'))
	);
</script>

<form
	class="composer"
	class:is-open={open}
	class:is-prayer={kind === 'prayer'}
	onsubmit={(e) => {
		e.preventDefault();
		save();
	}}
>
	{#if open}
		<!-- A daily prayer stays one; only a note and a prayer trade places. -->
		<div class="mb-3 flex flex-wrap items-center justify-between gap-2" hidden={kind === 'daily'}>
			<div class="seg" role="group" aria-label={t('notebook.entryKind')}>
				<button type="button" class:active={kind === 'note'} aria-pressed={kind === 'note'} onclick={() => (kind = 'note')}>
					✎ {t('reader.note')}
				</button>
				<button type="button" class:active={kind === 'prayer'} aria-pressed={kind === 'prayer'} onclick={() => (kind = 'prayer')}>
					🙏 {t('notebook.prayer')}
				</button>
			</div>
		</div>
		<input
			class="title-line"
			bind:value={title}
			maxlength={TITLE_MAX}
			placeholder={t('notebook.titlePlaceholder')}
			aria-label={t('notebook.titleLabel')}
			{onkeydown}
		/>
	{/if}
	{#if open}
		<!-- Formatting: stored as the marks a reader could type (**bold**, - list),
		     shown formatted in the Notebook. -->
		<div class="format" role="toolbar" aria-label={t('notebook.formatLabel')}>
			<button type="button" onclick={() => format('bold')} title="{t('notebook.formatBold')} (Ctrl/⌘ B)" aria-label={t('notebook.formatBold')}
				><strong>B</strong></button
			>
			<button type="button" onclick={() => format('italic')} title="{t('notebook.formatItalic')} (Ctrl/⌘ I)" aria-label={t('notebook.formatItalic')}
				><em>I</em></button
			>
			<button type="button" onclick={() => format('list')} title={t('notebook.formatList')} aria-label={t('notebook.formatList')}
				>•&thinsp;≡</button
			>
			<button type="button" onclick={() => format('quote')} title={t('notebook.formatQuote')} aria-label={t('notebook.formatQuote')}
				>❝</button
			>
		</div>
	{/if}
	<!-- svelte-ignore a11y_autofocus -- an edit opens because the reader asked to write -->
	<textarea
		bind:this={sheet}
		class="ruled"
		bind:value={body}
		maxlength={BODY_MAX}
		rows={open ? 5 : 1}
		{placeholder}
		aria-label={placeholder}
		autofocus={editing}
		onfocus={() => (open = true)}
		{onkeydown}
	></textarea>
	{#if open && kind === 'prayer'}
		<!-- Who the prayer is for, and which group of the prayer list it joins. -->
		<div class="mt-3 flex flex-wrap items-center gap-2">
			<input
				class="field person-field"
				bind:value={person}
				list={listId}
				maxlength={PERSON_MAX}
				placeholder={t('notebook.personPlaceholder')}
				aria-label={t('notebook.personLabel')}
				{onkeydown}
			/>
			<datalist id={listId}>
				{#each people as name (name)}<option value={name}></option>{/each}
			</datalist>
			<div class="flex flex-wrap gap-1.5" role="group" aria-label={t('notebook.groupLabel')}>
				{#each PRAYER_GROUPS as g (g)}
					<button
						type="button"
						class="chip"
						class:active={group === g}
						aria-pressed={group === g}
						onclick={() => (group = group === g ? '' : g)}>{t(`notebook.group_${g}`)}</button
					>
				{/each}
			</div>
		</div>
	{/if}
	{#if open}
		<div class="mt-3 flex flex-wrap gap-2">
			<input
				class="field ref-field grow"
				bind:value={ref}
				maxlength={REF_MAX}
				placeholder={t('notebook.refPlaceholder')}
				aria-label={t('notebook.refLabel')}
				{onkeydown}
			/>
			<input
				class="field collection-field"
				bind:value={collection}
				list={collectionListId}
				maxlength={COLLECTION_MAX}
				placeholder={t('notebook.collectionPlaceholder')}
				aria-label={t('notebook.collectionLabel')}
				{onkeydown}
			/>
			<datalist id={collectionListId}>
				{#each collectionNames as name (name)}<option value={name}></option>{/each}
			</datalist>
		</div>
		<div class="mt-4 flex flex-wrap items-center justify-end gap-2">
			<DictateButton ontext={(said) => (body = appendPhrase(body, said))} />
			<span class="me-auto text-micro text-muted">{t('notebook.saveHint')}</span>
			<button
				type="button"
				class="btn btn-ghost btn-sm"
				onclick={() => {
					if (oncancel) oncancel();
					else reset();
				}}
			>
				{t('common.cancel')}
			</button>
			<button type="submit" class="btn btn-primary btn-sm" disabled={!canSave}>
				{kind === 'prayer' ? t('notebook.savePrayer') : t('notebook.saveNote')}
			</button>
		</div>
	{/if}
</form>

<style>
	.composer {
		--rule-gap: 2rem;
		padding: 1rem 1.1rem;
		border: 1px dashed var(--border-strong);
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--surface) 70%, transparent);
		transition: border-color var(--duration-fast) ease;
	}
	.composer.is-open {
		border-style: solid;
		border-color: var(--accent-soft-border);
		box-shadow: var(--shadow-card);
	}
	.composer:focus-within {
		border-color: var(--accent);
	}
	.composer.is-prayer.is-open {
		border-color: color-mix(in srgb, var(--gold) 45%, transparent);
	}
	.title-line {
		width: 100%;
		border: none;
		border-bottom: 1px solid var(--border-strong);
		background: transparent;
		padding: 0.25rem 0;
		margin-bottom: 0.5rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		color: var(--text);
	}
	.title-line:focus {
		outline: none;
		border-bottom-color: var(--accent);
	}
	.title-line::placeholder {
		color: var(--muted);
		font-weight: 400;
	}
	/* Ruled paper: the line-height is the rule gap, and the background scrolls
	   with the text (attachment: local), so every line of writing sits on a rule. */
	.format {
		display: flex;
		gap: 0.15rem;
		margin-bottom: 0.25rem;
	}
	.format button {
		min-width: 2rem;
		padding: 0.15rem 0.45rem;
		border-radius: var(--radius-sm);
		font-family: var(--font-display);
		color: var(--muted);
		cursor: pointer;
	}
	.format button:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.ruled {
		display: block;
		width: 100%;
		resize: vertical;
		border: none;
		background-color: transparent;
		background-image: linear-gradient(
			to bottom,
			transparent calc(var(--rule-gap) - 1px),
			color-mix(in srgb, var(--accent) 22%, transparent) calc(var(--rule-gap) - 1px)
		);
		background-size: 100% var(--rule-gap);
		background-attachment: local;
		line-height: var(--rule-gap);
		padding: 0;
		font-family: var(--font-display);
		font-size: var(--fs-body);
		color: var(--text);
		min-height: var(--rule-gap);
	}
	.ruled:focus {
		outline: none;
	}
	.ruled::placeholder {
		color: var(--muted);
		font-style: italic;
	}
	.ref-field {
		font-style: italic;
	}
	.collection-field {
		flex: 1 1 12rem;
	}
	.person-field {
		flex: 1 1 12rem;
	}
</style>
