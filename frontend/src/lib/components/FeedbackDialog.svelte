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

	interface Props {
		onClose: () => void;
		/** Which surface opened the dialog — recorded with the submission. */
		source?: FeedbackSource;
	}
	let { onClose, source = 'menu' }: Props = $props();

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
	let saving = $state(false);
	let sent = $state(false);
	let error = $state('');

	// Resolve the work from the path once, when the dialog opens.
	const context = feedbackContext(
		typeof window === 'undefined' ? '' : window.location.pathname
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
				content_language: getLang(),
				ui_locale: getLang(),
				...context
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
				<h2 class="mb-1 text-h3">{t('feedback.title')}</h2>
				<p class="mb-4 text-small text-muted">{t('feedback.intro')}</p>

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
					rows="5"
					class="field w-full"
					aria-label={t('feedback.title')}
					placeholder={t('feedback.placeholder')}
				></textarea>

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
</style>
