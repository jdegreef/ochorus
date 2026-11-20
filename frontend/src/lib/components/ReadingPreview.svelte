<script lang="ts">
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A small page of reading, set by the REAL reading styles: the `.reading`
	 * class from app.css under `readerPrefs.style`, so the face, size, leading,
	 * measure and the illuminated opening initial are the ones a chapter will
	 * use, and the ground and ink are the applied theme and palette. Every
	 * choice in Settings' Appearance and Reading sections is visual; this lets
	 * the reader see it as they make it.
	 *
	 * The column is the chosen measure capped at the space Settings has, so
	 * Narrow and Normal visibly differ even where Extra wide cannot fit.
	 */
	const t = i18n.t;
</script>

<figure class="preview" aria-label={t('settings.preview')}>
	<figcaption class="cap">{t('settings.preview')}</figcaption>
	<div class="sheet">
		<div class="reading has-initial col" style={readerPrefs.style}>
			<p>{t('settings.previewText')}</p>
		</div>
	</div>
</figure>

<style>
	.preview {
		margin: 0 0 1.5rem;
		padding: 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.cap {
		font-size: var(--fs-micro);
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--muted);
		margin-block-end: 0.5rem;
	}
	.sheet {
		background: var(--bg);
		border-radius: var(--radius-sm);
		padding: 1rem 1.25rem;
		box-shadow: 0 8px 20px -14px rgb(0 0 0 / 0.45);
		overflow: hidden;
	}
	.col {
		max-inline-size: min(100%, var(--reading-measure));
		margin-inline: auto;
	}
	.col p {
		margin: 0;
	}
</style>
