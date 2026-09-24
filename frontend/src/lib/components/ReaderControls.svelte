<script lang="ts">
	import {
		readerPrefs,
		cssAlign,
		fontLabel,
		FONT_STACK,
		READER_FONTS,
		type Align,
		type Leading,
		type Margin,
		type Measure
	} from '$lib/readerPrefs.svelte';
	import { onDestroy } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { theme } from '$lib/theme.svelte';
	import { dismissable } from '$lib/actions/dismissable';

	let {
		/**
		 * Show the scroll-vs-page layout switch.
		 *
		 * Only the chapter reader implements paged mode — it needs a fixed
		 * viewport, page measuring, turning and a scrubber, none of which lives
		 * in <Reader> (which deliberately owns the prose, not the container).
		 * Sermons and biographies mount these same controls, so before this prop
		 * they showed a Scroll/Page switch that did NOTHING on their page and,
		 * because readerPrefs.paged is persisted, silently changed how the
		 * reader's next CHAPTER behaved.
		 *
		 * Defaults to false so the failure mode is safe: a new reading surface
		 * hides a control it can't honour rather than lying about one. When
		 * paged mode is shared (design review items 2-3), pass it everywhere.
		 */
		layout = false,
		/**
		 * Show the Margins group. Same rule as `layout`: only a surface whose
		 * article actually consumes `--reading-margin` may offer it — today the
		 * chapter reader's `.reading-article`. Sermons and biographies don't, so
		 * on them the control would persist a pref and change nothing, which
		 * `readerSurfaces.test.ts` exists to forbid. Defaults to hidden so a new
		 * surface fails safe.
		 */
		margins = false,
		/**
		 * A line of the reader's OWN text, shown at the top of the panel restyled
		 * live as size/spacing/typeface change — a preview that is the actual
		 * prose rather than a translated sample sentence. Omit (sermons, bios)
		 * and no preview renders.
		 */
		sample = '',
		/**
		 * The alignment to show as active. Defaults to the stored `align`, which is
		 * right for scroll surfaces; the paged chapter reader passes its layout-
		 * derived value (`effectiveAlign`) so the highlight matches what's on the
		 * page when paged mode is justifying by default. Clicking still records an
		 * explicit choice via `setAlign`.
		 */
		align = undefined
	}: { layout?: boolean; margins?: boolean; sample?: string; align?: Align } = $props();

	const activeAlign = $derived(align ?? readerPrefs.align);

	// Shared, not local: the reader's keyboard handler has to know a panel is
	// open so it stops turning pages under it (see readerUi.panelOpen).
	const open = {
		get value() {
			return readerUi.panelOpen;
		},
		set value(v: boolean) {
			readerUi.panelOpen = v;
		}
	};
	const t = i18n.t;

	// The flag lives on a module singleton so the reader's key handler can see
	// it; that outlives this component, so it has to be cleared on the way out.
	// Otherwise a back-swipe with the panel open leaves the next chapter mounting
	// with it "open" and the arrow keys swallowed.
	onDestroy(() => (readerUi.panelOpen = false));

	/** Paper / Sepia / Lamplight, in that order — lightest to darkest. */
	const THEMES: { v: 'light' | 'sepia' | 'dark'; k: string }[] = [
		{ v: 'light', k: 'settings.themeLight' },
		{ v: 'sepia', k: 'settings.themeSepia' },
		{ v: 'dark', k: 'settings.themeDark' }
	];
	const LEADINGS: { v: Leading; k: string }[] = [
		{ v: 'compact', k: 'spacing.compact' },
		{ v: 'normal', k: 'spacing.normal' },
		{ v: 'relaxed', k: 'spacing.relaxed' }
	];
	const MEASURES: { v: Measure; k: string }[] = [
		{ v: 'narrow', k: 'width.narrow' },
		{ v: 'normal', k: 'width.normal' },
		{ v: 'wide', k: 'width.wide' },
		{ v: 'xwide', k: 'width.xwide' }
	];
	/** Side gutters (scroll mode). Own keys, not the Width ones: "Margins" is
	 *  plural in most locales and the adjectives must agree with it. */
	const MARGINS: { v: Margin; k: string }[] = [
		{ v: 'narrow', k: 'margin.narrow' },
		{ v: 'normal', k: 'margin.normal' },
		{ v: 'generous', k: 'margin.generous' }
	];
	const FONT_KINDS = {
		serif: t('font.serif'),
		sans: t('font.sans'),
		dyslexic: t('font.dyslexic')
	};
	const ALIGNMENTS: { v: Align; k: string }[] = [
		{ v: 'left', k: 'align.left' },
		{ v: 'justify', k: 'align.justify' }
	];
</script>

<div
	class="relative"
	use:dismissable={{ open: open.value, onDismiss: () => (open.value = false) }}
>
	<button
		class="btn btn-sm btn-ghost"
		onclick={() => (open.value = !open.value)}
		aria-haspopup="dialog"
		aria-expanded={open.value}
		aria-label={t('reader.textSettings')}
	>
		<span class="font-display">A</span><span class="text-small">a</span>
	</button>

	{#if open.value}
		<div
			class="absolute end-0 z-30 mt-2 max-h-[70vh] w-64 overflow-y-auto rounded-card border border-border bg-surface p-4 shadow-lg"
			role="dialog"
			aria-label={t('reader.textSettings')}
		>
			<!-- Live preview: the chapter's own opening line, restyled as the
			     controls change, so a size/spacing/typeface choice shows its
			     effect on the real prose before you close the panel. -->
			{#if sample}
				<!-- `reading` supplies the face/size/leading from the same custom
				     properties the article consumes (one definition, in app.css);
				     `dir="auto"` because this is content prose inside localized
				     chrome — see readerDirection.test.ts. -->
				<!-- Kept on one source line: readerDirection.test.ts matches
				     `rc-preview mb-3` and dir="auto" on the same line. -->
				<div class="reading rc-preview mb-3" style="{readerPrefs.style}; text-align: {cssAlign(activeAlign)}" dir="auto" aria-hidden="true">
					{sample}
				</div>
			{/if}

			<!-- Font size -->
			<div class="mb-3 flex items-center justify-between">
				<span class="text-small font-semibold text-text">{t('reader.size')}</span>
				<div class="flex items-center gap-1">
					<button
						class="btn btn-sm btn-ghost"
						onclick={() => readerPrefs.bumpScale(-0.1)}
						aria-label={t('a11y.smallerText')}>A−</button
					>
					<span class="w-10 text-center text-small text-muted"
						>{Math.round(readerPrefs.scale * 100)}%</span
					>
					<button
						class="btn btn-sm btn-ghost text-body"
						onclick={() => readerPrefs.bumpScale(0.1)}
						aria-label={t('a11y.largerText')}>A+</button
					>
				</div>
			</div>

			<!-- Theme -->
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('nav.theme')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each THEMES as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={theme.current === o.v}
							class:text-accent={theme.current === o.v}
							class:border-border-strong={theme.current !== o.v}
							class:text-muted={theme.current !== o.v}
							onclick={() => theme.set(o.v)}
							aria-pressed={theme.current === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Leading -->
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.spacing')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each LEADINGS as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={readerPrefs.leading === o.v}
							class:text-accent={readerPrefs.leading === o.v}
							class:border-border-strong={readerPrefs.leading !== o.v}
							class:text-muted={readerPrefs.leading !== o.v}
							onclick={() => readerPrefs.setLeading(o.v)}
							aria-pressed={readerPrefs.leading === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Measure / width -->
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.width')}</span>
				<div class="grid grid-cols-2 gap-1">
					{#each MEASURES as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={readerPrefs.measure === o.v}
							class:text-accent={readerPrefs.measure === o.v}
							class:border-border-strong={readerPrefs.measure !== o.v}
							class:text-muted={readerPrefs.measure !== o.v}
							onclick={() => readerPrefs.setMeasure(o.v)}
							aria-pressed={readerPrefs.measure === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Margins: the column's side gutters in scroll mode. Width sets how
			     wide the text runs; this is the space between it and the screen
			     edge — the knob a tablet reader reaches for when the column floats.
			     Only where the surface honours it (`margins`), and not in page
			     mode, which zeroes the article padding and keeps its own gutters. -->
			{#if margins && !readerPrefs.paged}
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.margins')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each MARGINS as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={readerPrefs.margin === o.v}
							class:text-accent={readerPrefs.margin === o.v}
							class:border-border-strong={readerPrefs.margin !== o.v}
							class:text-muted={readerPrefs.margin !== o.v}
							onclick={() => readerPrefs.setMargin(o.v)}
							aria-pressed={readerPrefs.margin === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>
			{/if}

			<!-- Typeface -->
			<div>
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.typeface')}</span>
				<!-- Each option is set in its own face: a typeface is chosen by looking
				     at it. That fetches each face's latin file the first time the panel
				     opens (nothing before), which is the price of a preview. -->
				<div class="grid grid-cols-2 gap-1">
					{#each READER_FONTS as v (v)}
						<button
							class="rc-opt truncate rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={readerPrefs.font === v}
							class:text-accent={readerPrefs.font === v}
							class:border-border-strong={readerPrefs.font !== v}
							class:text-muted={readerPrefs.font !== v}
							style:font-family={FONT_STACK[v]}
							onclick={() => readerPrefs.setFont(v)}
							aria-pressed={readerPrefs.font === v}>{fontLabel(v, FONT_KINDS)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Text alignment -->
			<div class="mt-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.alignment')}</span>
				<div class="grid grid-cols-2 gap-1">
					{#each ALIGNMENTS as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={activeAlign === o.v}
							class:text-accent={activeAlign === o.v}
							class:border-border-strong={activeAlign !== o.v}
							class:text-muted={activeAlign !== o.v}
							onclick={() => readerPrefs.setAlign(o.v)}
							aria-pressed={activeAlign === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Layout: continuous scroll vs. paged (page-turn) reading. Below the
			     type controls — it's a mode switch, changed far less often than size
			     or spacing. Listening (voice + speed) lives in Settings → Reading.
			     Only rendered where the surface actually implements paged mode. -->
			{#if layout}
			<div class="mt-3 border-t border-border pt-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.layout')}</span>
				<div class="grid grid-cols-2 gap-1">
					<button
						class="rc-opt rounded-sm border px-2 py-1.5 text-small"
						class:border-accent={!readerPrefs.paged}
						class:text-accent={!readerPrefs.paged}
						class:border-border-strong={readerPrefs.paged}
						class:text-muted={readerPrefs.paged}
						onclick={() => readerPrefs.setPaged(false)}
						aria-pressed={!readerPrefs.paged}>{t('reader.layoutScroll')}</button
					>
					<button
						class="rc-opt rounded-sm border px-2 py-1.5 text-small"
						class:border-accent={readerPrefs.paged}
						class:text-accent={readerPrefs.paged}
						class:border-border-strong={!readerPrefs.paged}
						class:text-muted={!readerPrefs.paged}
						onclick={() => readerPrefs.setPaged(true)}
						aria-pressed={readerPrefs.paged}>{t('reader.layoutPage')}</button
					>
				</div>
				<!-- Scroll-mode only: page mode already turns on a tap (left/right).
				     A single opt-in toggle, off by default — tapping the lower screen
				     scrolls down a page. -->
				{#if !readerPrefs.paged}
					<button
						class="rc-opt mt-1.5 w-full rounded-sm border px-2 py-1.5 text-small"
						class:border-accent={readerPrefs.tapToScroll}
						class:text-accent={readerPrefs.tapToScroll}
						class:border-border-strong={!readerPrefs.tapToScroll}
						class:text-muted={!readerPrefs.tapToScroll}
						onclick={() => readerPrefs.setTapToScroll(!readerPrefs.tapToScroll)}
						aria-pressed={readerPrefs.tapToScroll}>{t('reader.tapScroll')}</button
					>
				{/if}
			</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	/* Face, size and leading come from the global `.reading` (app.css) — the one
	   definition the article uses, so retuning it retunes this. This only adds
	   the alignment and the chrome, bounded to two lines so a 1.6x size can't
	   balloon the panel. */
	.rc-preview {
		text-align: var(--reading-align, start);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		padding: 0.35rem 0.5rem;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
	}
</style>
