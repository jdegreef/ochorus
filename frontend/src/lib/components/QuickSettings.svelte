<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme, THEME_OPTIONS } from '$lib/theme.svelte';
	import { palette } from '$lib/palette.svelte';
	import { PALETTES, swatchOf } from '$lib/palettes';
	import { siteFont, SITE_FONTS, SITE_FONT_LABEL_KEY, type SiteFont } from '$lib/siteFont.svelte';
	import { FONT_STACK } from '$lib/readerPrefs.svelte';
	import { radioKeys } from '$lib/radioKeys';
	import { localizeHref } from '$lib/href';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import { i18n } from '$lib/i18n.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { dismissable } from '$lib/actions/dismissable';

	// Take Root's quick-settings popover: the gear opens a small menu with the
	// look of the site — brightness (system / light / sepia / dark), library
	// colours, site style — and a page-width stepper, with no navigation to the
	// Settings page. Every control drives the same store Settings does (the
	// stepper, the shared pageWidth that every `.page-col` follows).
	const t = i18n.t;
	let open = $state(false);

	// A chapter and a sermon size their column from `--reading-measure`, which
	// their own `A a` popover owns — `.page-col` isn't on those pages at all. The
	// stepper still rendered there and still WORKED, in the sense that it stored a
	// new value and moved nothing: a width control sitting a few pixels from the
	// width control that does something. Hide the row rather than leave it lying;
	// the theme, colour and style groups below still apply everywhere.
	const inReader = $derived(isReaderRoute($page.route.id));

	onMount(() => pageWidth.init());

	// Swatches draw in the brightness showing (a dark ground under dark), like
	// PalettePicker's cards: a preview of the applied palette would show nothing.
	const mode = $derived(theme.current === 'dark' ? 'dark' : 'light');

	// Each site style says "Aa" in its own face — the stacks the reader's font
	// list already holds (and fontStacks.test.ts already checks).
	const FACE: Record<SiteFont, string> = {
		house: FONT_STACK.serif,
		classic: FONT_STACK.garamond,
		hyperlegible: FONT_STACK.hyperlegible
	};

	const THEME_PREFS = THEME_OPTIONS.map((o) => o.v);
	const themeKeys = radioKeys(THEME_PREFS, () => theme.preference, (v) => theme.set(v), 'data-theme-option');
	const paletteKeys = radioKeys(PALETTES, () => palette.current, (v) => palette.set(v), 'data-palette-option');
	const fontKeys = radioKeys(SITE_FONTS, () => siteFont.current, (v) => siteFont.set(v), 'data-font-option');
</script>

<div class="prefs" use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<!-- aria-controls only while the panel exists: it is rendered by {#if open},
	     and an IDREF pointing at nothing is worse than none. aria-expanded stays
	     on both states — that IS the closed state's information. -->
	<button
		class="prefs-btn"
		aria-expanded={open}
		aria-controls={open ? 'quick-settings' : undefined}
		aria-label={t('settings.title')}
		title={t('settings.title')}
		onclick={() => (open = !open)}
	>
		<Icon name="gear" size={19} />
		<!-- The palette in use, as a dot on the gear: says there are colours in
		     here to choose. Hidden on the house palette, where it would say
		     nothing. -->
		{#if palette.current !== 'parchment'}
			<span class="prefs-badge" aria-hidden="true"></span>
		{/if}
	</button>
	{#if open}
		<!-- A labelled GROUP of controls, not a menu. role="menu" promises
		     menuitem children and arrow-key navigation between them; this popover
		     holds radio groups (and, off the reading surfaces, a width stepper)
		     with their labels, and under that role a screen reader hides the
		     labels as foreign content and announces a menu whose items don't
		     respond to the keys it just promised. It borrows the account menu's
		     LOOK, not its semantics. -->
		<div id="quick-settings" class="account-menu prefs-menu" role="group" aria-label={t('settings.title')}>
			<div class="prefs-row">
				<span class="prefs-label" id="qs-theme">{t('nav.theme')}</span>
				<div class="seg prefs-seg" role="radiogroup" aria-labelledby="qs-theme" tabindex="-1" onkeydown={themeKeys}>
					{#each THEME_OPTIONS as o (o.v)}
						<button
							type="button"
							role="radio"
							aria-checked={theme.preference === o.v}
							class:active={theme.preference === o.v}
							tabindex={theme.preference === o.v ? 0 : -1}
							data-theme-option={o.v}
							aria-label={t(o.k)}
							title={t(o.k)}
							onclick={() => theme.set(o.v)}
						>
							<Icon name={o.icon} size={17} />
						</button>
					{/each}
				</div>
			</div>
			<div class="prefs-row prefs-row--stack">
				<span class="prefs-label" id="qs-palette">{t('settings.palette')}</span>
				<div
					class="prefs-swatches"
					role="radiogroup"
					aria-labelledby="qs-palette"
					tabindex="-1"
					onkeydown={paletteKeys}
				>
					{#each PALETTES as p (p)}
						{@const [ground, accent, second, mark] = swatchOf(p, mode)}
						<button
							type="button"
							role="radio"
							aria-checked={palette.current === p}
							tabindex={palette.current === p ? 0 : -1}
							data-palette-option={p}
							aria-label={t(`palette.${p}`)}
							title={t(`palette.${p}`)}
							class="prefs-swatch"
							style:--sw-ground={ground}
							style:--sw-accent={accent}
							style:--sw-second={second}
							style:background={mark}
							onclick={() => palette.set(p)}
						></button>
					{/each}
				</div>
			</div>
			<div class="prefs-row prefs-row--stack">
				<span class="prefs-label" id="qs-font">{t('settings.siteFont')}</span>
				<div class="seg prefs-seg" role="radiogroup" aria-labelledby="qs-font" tabindex="-1" onkeydown={fontKeys}>
					{#each SITE_FONTS as f (f)}
						<button
							type="button"
							role="radio"
							aria-checked={siteFont.current === f}
							class:active={siteFont.current === f}
							tabindex={siteFont.current === f ? 0 : -1}
							data-font-option={f}
							aria-label={t(SITE_FONT_LABEL_KEY[f])}
							title={t(SITE_FONT_LABEL_KEY[f])}
							class="prefs-font"
							style:font-family={FACE[f]}
							onclick={() => siteFont.set(f)}
						>
							<span aria-hidden="true">Aa</span>
						</button>
					{/each}
				</div>
			</div>
			{#if !inReader}
				<div class="prefs-row">
					<span class="prefs-label">{t('nav.pageWidth')}</span>
					<div class="widthctl">
						<button
							onclick={() => pageWidth.step(-1)}
							disabled={pageWidth.atMin}
							aria-label={t('a11y.narrower')}
							title={t('a11y.narrower')}
						>
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path d="M3 12h6" /><path d="M6 9l3 3-3 3" />
								<path d="M21 12h-6" /><path d="M18 9l-3 3 3 3" />
							</svg>
						</button>
						<button
							onclick={() => pageWidth.step(1)}
							disabled={pageWidth.atMax}
							aria-label={t('a11y.wider')}
							title={t('a11y.wider')}
						>
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path d="M9 12H3" /><path d="M6 9l-3 3 3 3" />
								<path d="M15 12h6" /><path d="M18 9l3 3-3 3" />
							</svg>
						</button>
					</div>
				</div>
			{/if}
			<a class="prefs-more" href={localizeHref('/settings')} onclick={() => (open = false)}>
				{t('settings.title')}
				<Icon name="chevron-right" size={14} />
			</a>
		</div>
	{/if}
</div>
