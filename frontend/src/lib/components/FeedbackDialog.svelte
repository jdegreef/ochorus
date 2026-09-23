<script lang="ts">
	/**
	 * The reader feedback modal: pick a type, write a note, send.
	 *
	 * Same shape as NoteDialog — a fixed overlay + focus-trapped card, host-owned
	 * open state (the parent renders it with `{#if}`) and an `onClose` callback.
	 * It captures the page it was opened on (URL + the resolved work, when the
	 * page is a book/sermon/…) so a language note carries "which book, which
	 * chapter" without asking. Signed-in only — the parent gates on `auth.user`.
	 */
	import { i18n } from '$lib/i18n.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { getLang } from '$lib/lang.svelte';
	import { feedbackContext } from '$lib/feedbackContext';
	import { submitFeedback, type FeedbackCategory, type FeedbackSource } from '$lib/library-public';

	/** When the dialog is opened from a text selection (highlight-to-feedback):
	 *  the quote to comment on, plus the work context the reader gives us
	 *  authoritatively (so we don't re-parse the URL). */
	interface SelectionInfo {
		text: string;
		anchorBlock?: number;
		contentKind?: string;
		contentSlug?: string;
		chapterRef?: string;
		contentLanguage?: string;
	}

	interface Props {
		onClose: () => void;
		/** Which surface opened the dialog — recorded with the submission. */
		source?: FeedbackSource;
		/** Present when opened from a highlighted selection. */
		selection?: SelectionInfo;
	}
	let { onClose, source = 'menu', selection }: Props = $props();

	const t = i18n.t;

	const CATEGORIES: { value: FeedbackCategory; label: string }[] = [
		{ value: 'language', label: 'feedback.typeLanguage' },
		{ value: 'content', label: 'feedback.typeContent' },
		{ value: 'feature', label: 'feedback.typeFeature' },
		{ value: 'bug', label: 'feedback.typeBug' },
		{ value: 'other', label: 'feedback.typeOther' }
	];

	let category = $state<FeedbackCategory>('language');
	let body = $state('');
	let suggested = $state('');
	let saving = $state(false);
	let sent = $state(false);
	let error = $state('');

	// Prefer the context the selection gives us; otherwise resolve it from the path.
	const context = $derived(
		selection
			? {
					content_kind: selection.contentKind,
					content_slug: selection.contentSlug,
					chapter_ref: selection.chapterRef
				}
			: feedbackContext(typeof window === 'undefined' ? '' : window.location.pathname)
	);

	const canSubmit = $derived(body.trim().length >= 10 && !saving);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!canSubmit) return;
		saving = true;
		error = '';
		try {
			await submitFeedback({
				category,
				body: body.trim(),
				source,
				page_url: typeof window === 'undefined' ? '' : window.location.href,
				content_language: selection?.contentLanguage || getLang(),
				ui_locale: getLang(),
				...context,
				...(selection
					? {
							selected_text: selection.text,
							suggested_text: suggested.trim() || undefined,
							anchor_block: selection.anchorBlock
						}
					: {})
			});
			sent = true;
		} catch {
			error = t('feedback.error');
		} finally {
			saving = false;
		}
	}
</script>

<div
	class="fb-overlay"
	role="dialog"
	aria-modal="true"
	aria-label={t('feedback.title')}
	use:focusTrap={{ onEscape: onClose }}
>
	<div class="fb-card">
		{#if sent}
			<h2 class="mb-2 text-h3">{t('feedback.thanksTitle')}</h2>
			<p class="mb-4 text-body text-muted">{t('feedback.thanksBody')}</p>
			<div class="flex">
				<button class="btn btn-primary ms-auto" onclick={onClose}>{t('a11y.close')}</button>
			</div>
		{:else}
			<form onsubmit={submit}>
				<h2 class="mb-1 text-h3">{selection ? t('feedback.editTitle') : t('feedback.title')}</h2>
				<p class="mb-4 text-small text-muted">
					{selection ? t('feedback.editIntro') : t('feedback.intro')}
				</p>

				{#if selection}
					<blockquote class="fb-quote">{selection.text}</blockquote>
				{/if}

				<label class="mb-3 block">
					<span class="mb-1 block text-small text-muted">{t('feedback.type')}</span>
					<select class="field w-full" bind:value={category}>
						{#each CATEGORIES as c (c.value)}
							<option value={c.value}>{t(c.label)}</option>
						{/each}
					</select>
				</label>

				<textarea
					bind:value={body}
					rows={selection ? 3 : 5}
					class="field w-full"
					aria-label={t('feedback.title')}
					placeholder={t('feedback.placeholder')}
				></textarea>

				{#if selection}
					<label class="mt-3 block">
						<span class="mb-1 block text-small text-muted">{t('feedback.suggestedLabel')}</span>
						<textarea
							bind:value={suggested}
							rows="2"
							class="field w-full"
							placeholder={t('feedback.suggestedPlaceholder')}
						></textarea>
					</label>
				{/if}

				{#if context.content_slug}
					<p class="mt-2 text-small text-muted">
						{t('feedback.about')}: {context.content_slug}{context.chapter_ref
							? ` · ${context.chapter_ref}`
							: ''}
					</p>
				{/if}

				{#if error}
					<p class="mt-2 text-small text-danger">{error}</p>
				{/if}

				<div class="mt-4 flex items-center gap-2">
					<button type="button" class="btn btn-ghost ms-auto" onclick={onClose}
						>{t('common.cancel')}</button
					>
					<button type="submit" class="btn btn-primary" disabled={!canSubmit}>
						{saving ? t('feedback.sending') : t('feedback.submit')}
					</button>
				</div>
			</form>
		{/if}
	</div>
</div>

<style>
	.fb-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.fb-card {
		width: 100%;
		max-width: 32rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: var(--shadow-popover);
	}
	.fb-quote {
		margin: 0 0 0.75rem;
		max-height: 8rem;
		overflow-y: auto;
		border-inline-start: 3px solid var(--accent);
		background: var(--accent-soft);
		padding: 0.5rem 0.75rem;
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
		font-style: italic;
		color: var(--text);
		font-size: 0.95em;
	}
</style>
