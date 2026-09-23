<!--
	The things that float above read prose: the selection bar, the scripture
	and dictionary popovers, the listen bar, the note editor, and the Notebook
	dialog a passage can be written about or prayed from.

	They are a component of their own — rather than markup inside `Reader` —
	because they must be rendered OUTSIDE the element holding the prose. The
	chapter reader's page-turn mode puts a `translateX` on the container the prose
	sits in, and a `position: fixed` overlay inside a transformed ancestor is laid
	out against that ancestor rather than the viewport: every one of these would
	slide sideways with the page turn. Keeping them separate lets a surface place
	the prose where its layout needs it and these where the viewport is.
-->
<script lang="ts">
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';
	import NoteDialog from '$lib/components/NoteDialog.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { listen } from '$lib/listen.svelte';
	import { localizeHref } from '$lib/href';
	import type { EntrySource, JournalKind } from '$lib/journal';
	import type { EntryDraft } from '$lib/journal.svelte';
	import type { Segment } from '$lib/marks.svelte';
	import type { ReaderText } from '$lib/readerText.svelte';

	const t = i18n.t;

	let {
		reader,
		container,
		language
	}: {
		/** The shared machinery — see `$lib/readerText.svelte.ts`. */
		reader: ReaderText;
		/** The prose element the selection bar watches for selections. */
		container: HTMLElement | undefined;
		/**
		 * The edition's language. The quote card draws the reader's own sentence
		 * onto a canvas, where a font stack has to be named outright — so it needs
		 * to know the script to pick a face that can actually draw it. Required,
		 * as it is on SelectionBar: a quote card with no language falls back to a
		 * Latin stack, which cannot draw Arabic or Devanagari at all.
		 */
		language: string;
	} = $props();

	/** The passage being written about, while the Notebook dialog is open. */
	let writing = $state<{ kind: JournalKind; source: EntrySource } | null>(null);
	/** "Saved to your Notebook", briefly, after it closes. */
	let saved = $state(false);
	let savedTimer: ReturnType<typeof setTimeout>;

	// The Notebook's dialog and store load on first use, not with every chapter:
	// most readings never open them, and the store reads the whole journal on load.
	type Dialog = typeof import('$lib/components/notebook/JournalDialog.svelte').default;
	let JournalDialog = $state<Dialog | null>(null);

	async function startJournal(kind: JournalKind, quote: string, segments: Segment[]) {
		const { cite, where } = reader;
		const source: EntrySource = {
			...where,
			// The paragraph the selection starts in — where the link lands.
			p: Math.min(...segments.map((s) => s.p)),
			title: cite.chapter ? `${cite.book} · ${cite.chapter}` : cite.book,
			quote: quote.slice(0, 600)
		};
		JournalDialog ??= (await import('$lib/components/notebook/JournalDialog.svelte')).default;
		writing = { kind, source };
	}

	async function saveJournal(draft: EntryDraft) {
		const source = writing?.source ?? null;
		const { journal } = await import('$lib/journal.svelte');
		journal.add(draft, source);
		writing = null;
		saved = true;
		clearTimeout(savedTimer);
		savedTimer = setTimeout(() => (saved = false), 5000);
	}

	// Highlight-to-feedback: the selection the reader is sending feedback on.
	// The quote is the durable anchor; the block index gives a deep-link back.
	let suggesting = $state<{
		text: string;
		anchorBlock?: number;
		contentKind: string;
		contentSlug: string;
		chapterRef: string;
		contentLanguage: string;
	} | null>(null);

	function startSuggestEdit(quote: string, segments: Segment[]) {
		const { where } = reader;
		suggesting = {
			text: quote.slice(0, 2000),
			anchorBlock: segments.length ? Math.min(...segments.map((s) => s.p)) : undefined,
			contentKind: where.kind,
			contentSlug: where.slug,
			chapterRef: where.kind === 'book' ? String(where.order) : '',
			contentLanguage: language
		};
	}
</script>

<SelectionBar
	{container}
	{language}
	cite={reader.cite}
	onHighlight={reader.onHighlight}
	onNote={reader.openNoteForSelection}
	highlightColor={reader.highlightColor}
	onDefine={reader.onDefine}
	onDefineClose={reader.onDefineClose}
	onJournal={startJournal}
	onSuggestEdit={auth.user ? startSuggestEdit : undefined}
/>

<ScripturePopover />
<DefinePopover />
<ListenBar />

{#if listen.noVoice}
	<!-- The listener tapped Listen but no voice the reader would speak with
	     resolves for this edition, so playback would be silent — say so instead
	     of failing quietly. -->
	<div class="reader-dock listen-notice" role="status">
		<span class="min-w-0 text-small">{t('reader.listenNoVoice')}</span>
		<button
			class="btn btn-icon btn-ghost shrink-0"
			onclick={() => listen.dismissNoVoice()}
			aria-label={t('a11y.close')}
		>
			<Icon name="close" size={16} />
		</button>
	</div>
{/if}

{#if writing && JournalDialog}
	<JournalDialog
		kind={writing.kind}
		source={writing.source}
		onsave={saveJournal}
		onclose={() => (writing = null)}
	/>
{/if}

{#if saved}
	<!-- At the top, not in the bottom dock: the listen bar and its notices live
	     there, and this must not cover them. -->
	<div class="saved-notice" role="status">
		<span class="min-w-0 text-small">✓ {t('reader.savedToNotebook')}</span>
		<a class="btn btn-sm btn-ghost shrink-0" href={localizeHref('/notebook')}>{t('reader.openNotebook')}</a>
	</div>
{/if}

{#if reader.open}
	<NoteDialog
		bind:text={reader.draft}
		bind:color={reader.color}
		canRemove={!!reader.id}
		onSave={reader.saveNote}
		onRemove={reader.removeMark}
		onClose={reader.close}
	/>
{/if}

{#if suggesting}
	<FeedbackDialog source="highlight" selection={suggesting} onClose={() => (suggesting = null)} />
{/if}

<style>
	/* Dock chrome (fixed, glass, border) comes from `.reader-dock` in app.css;
	   these are the notice's own inline layout and padding. */
	.saved-notice {
		position: fixed;
		z-index: 45;
		top: calc(env(safe-area-inset-top) + 4.25rem);
		inset-inline: 0;
		margin-inline: auto;
		width: max-content;
		max-width: calc(100vw - 1.5rem);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.5rem 0.35rem 1rem;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		box-shadow: var(--shadow-popover);
	}
	.listen-notice {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		max-width: 48rem;
		margin-inline: auto;
		padding: 0.625rem 1rem;
		padding-bottom: calc(0.625rem + env(safe-area-inset-bottom));
	}
</style>
