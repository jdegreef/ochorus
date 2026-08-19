<script lang="ts">
	import {
		readerPrefs,
		type Align,
		type Leading,
		type Measure,
		type ReaderFont
	} from '$lib/readerPrefs.svelte';
	import { onDestroy } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { theme } from '$lib/theme.svelte';

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
		layout = false
	}: { layout?: boolean } = $props();

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
	let wrap = $state<HTMLDivElement>();
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
		{ v: 'wide', k: 'width.wide' }
	];
	const FONTS: { v: ReaderFont; k: string }[] = [
		{ v: 'serif', k: 'font.serif' },
		{ v: 'sans', k: 'font.sans' },
		{ v: 'dyslexic', k: 'font.dyslexic' }
	];
	const ALIGNMENTS: { v: Align; k: string }[] = [
		{ v: 'left', k: 'align.left' },
		{ v: 'justify', k: 'align.justify' }
	];

	function onWindowClick(e: MouseEvent) {
		if (open.value && wrap && !wrap.contains(e.target as Node)) open.value = false;
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open.value = false;
	}
</script>

<svelte:window onclick={onWindowClick} onkeydown={onKey} />

<div class="relative" bind:this={wrap}>
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
			class="absolute end-0 z-30 mt-2 w-64 rounded-card border border-border bg-surface p-4 shadow-lg"
			role="dialog"
			aria-label={t('reader.textSettings')}
		>
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
						class="btn btn-sm btn-ghost text-base"
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
				<div class="grid grid-cols-3 gap-1">
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

			<!-- Typeface -->
			<div>
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.typeface')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each FONTS as o (o.v)}
						<button
							class="rc-opt rounded-sm border px-2 py-1.5 text-small"
							class:border-accent={readerPrefs.font === o.v}
							class:text-accent={readerPrefs.font === o.v}
							class:border-border-strong={readerPrefs.font !== o.v}
							class:text-muted={readerPrefs.font !== o.v}
							onclick={() => readerPrefs.setFont(o.v)}
							aria-pressed={readerPrefs.font === o.v}>{t(o.k)}</button
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
							class:border-accent={readerPrefs.align === o.v}
							class:text-accent={readerPrefs.align === o.v}
							class:border-border-strong={readerPrefs.align !== o.v}
							class:text-muted={readerPrefs.align !== o.v}
							onclick={() => readerPrefs.setAlign(o.v)}
							aria-pressed={readerPrefs.align === o.v}>{t(o.k)}</button
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
			</div>
			{/if}
		</div>
	{/if}
</div>
