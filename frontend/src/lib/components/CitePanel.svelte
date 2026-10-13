<script lang="ts">
	import { CITATION_STYLES, cite, type Citable, type CitationStyle } from '$lib/citation';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * "Cite this book" / "Cite this sermon": a quiet disclosure under the page's
	 * rights line, for the student or preacher who needs the work in a
	 * bibliography or a footnote. Each style is shown in full and copies with
	 * its italics where the clipboard takes HTML (a word processor keeps them),
	 * as plain text where it doesn't. The styles are English conventions, so the
	 * line is English, left to right; the title keeps its own language and
	 * direction.
	 */
	let { work, lang }: { work: Citable; /** The edition's language, for its title. */ lang: string } = $props();
	const t = i18n.t;

	const citations = $derived(CITATION_STYLES.map((s) => ({ ...s, ...cite(work, s.style) })));

	let copied = $state<CitationStyle | null>(null);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	async function copy(c: (typeof citations)[number]) {
		try {
			// BibTeX is code: an HTML flavour would collapse its lines in a rich editor.
			if (c.style !== 'bibtex' && typeof ClipboardItem !== 'undefined' && navigator.clipboard.write) {
				await navigator.clipboard.write([
					new ClipboardItem({
						'text/plain': new Blob([c.text], { type: 'text/plain' }),
						'text/html': new Blob([c.html], { type: 'text/html' })
					})
				]);
			} else {
				await navigator.clipboard.writeText(c.text);
			}
			copied = c.style;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = null), 2000);
		} catch {
			// A denied clipboard: the citation is on the page, selectable.
		}
	}
</script>

<details class="cite mt-3 text-small">
	<summary class="text-muted">{t(work.kind === 'book' ? 'cite.book' : 'cite.sermon')}</summary>
	<p class="mt-2 text-muted">{t('cite.note')}</p>
	<dl class="mt-3 space-y-3">
		{#each citations as c (c.style)}
			<div class="rounded-card border border-border bg-surface p-3">
				<dt class="flex items-center justify-between gap-3">
					<span class="text-eyebrow text-muted">{c.label}</span>
					<button type="button" class="btn btn-sm btn-ghost" onclick={() => copy(c)}
						>{copied === c.style ? t('quotes.copied') : t('quotes.copy')}<span class="sr-only">: {c.label}</span></button
					>
				</dt>
				<dd class="mt-1 text-text" class:bibtex={c.style === 'bibtex'} lang="en" dir="ltr">
					{#each c.parts as p, i (i)}{#if typeof p === 'string'}{p}{:else if p.italic}<i
								><bdi {lang}>{p.title}</bdi></i
							>{:else}<bdi {lang}>{p.title}</bdi>{/if}{/each}
				</dd>
			</div>
		{/each}
	</dl>
</details>

<style>
	.cite summary {
		cursor: pointer;
		width: fit-content;
	}
	.cite summary:hover {
		color: var(--color-text);
	}
	.cite dd {
		overflow-wrap: anywhere;
	}
	.bibtex {
		white-space: pre-wrap;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.85em;
	}
</style>
