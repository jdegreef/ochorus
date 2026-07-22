<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { theme } from '$lib/theme.svelte';
	import { lang } from '$lib/lang.svelte';
	import { readerPrefs, FONT_STACK, MEASURE, type ReaderFont, type Measure } from '$lib/readerPrefs.svelte';
	import { listen, RATES } from '$lib/listen.svelte';
	import { readingSync } from '$lib/readingSync';
	import { collectExport, toMarkdown, downloadFile } from '$lib/dataExport';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	const t = i18n.t;

	type Section = 'profile' | 'reading' | 'appearance';
	const SECTIONS: { id: Section; label: string; icon: IconName }[] = [
		{ id: 'profile', label: t('settings.navProfile'), icon: 'users' },
		{ id: 'reading', label: t('settings.navReading'), icon: 'book' },
		{ id: 'appearance', label: t('settings.navAppearance'), icon: 'sun' }
	];
	// The active section lives in the URL (?section=…) so it survives the full
	// reload a language change triggers, and so it's shareable/back-navigable.
	const isSection = (s: string | null): s is Section =>
		s === 'profile' || s === 'reading' || s === 'appearance';
	const initial = $page.url.searchParams.get('section');
	let section = $state<Section>(isSection(initial) ? initial : 'profile');

	function selectSection(id: Section) {
		section = id;
		const url = new URL($page.url);
		url.searchParams.set('section', id);
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	const FONTS: { id: ReaderFont; label: string }[] = [
		{ id: 'serif', label: t('settings.fontSerif') },
		{ id: 'sans', label: t('settings.fontSans') },
		{ id: 'dyslexic', label: t('settings.fontDyslexic') }
	];
	const WIDTHS = Object.keys(MEASURE) as Measure[];

	// Export my data — assemble the bundle (fetches catalogs for titles) then hand
	// the reader a JSON or Markdown file. Device-local; works signed in or out.
	let exporting = $state<'json' | 'md' | null>(null);
	async function exportData(format: 'json' | 'md') {
		if (exporting) return;
		exporting = format;
		try {
			const bundle = await collectExport(lang.current, new Date().toISOString());
			if (format === 'json') {
				downloadFile('ochorus-data.json', 'application/json', JSON.stringify(bundle, null, 2));
			} else {
				downloadFile('ochorus-reading.md', 'text/markdown;charset=utf-8', toMarkdown(bundle));
			}
		} finally {
			exporting = null;
		}
	}

	// Display name — editable profile field. Seeded from the profile until the
	// reader edits it (nameDirty), so a late profile load can't clobber typing.
	let nameInput = $state(auth.displayName);
	let nameDirty = $state(false);
	let nameSaving = $state(false);
	$effect(() => {
		if (!nameDirty) nameInput = auth.displayName;
	});
	const nameChanged = $derived(nameInput.trim() !== auth.displayName);
	async function saveName() {
		if (nameSaving || !nameChanged) return;
		nameSaving = true;
		try {
			await auth.setDisplayName(nameInput);
			nameDirty = false;
		} finally {
			nameSaving = false;
		}
	}

	// Sync visibility — surface the otherwise-invisible cross-device sync: when it
	// last succeeded and a manual "Sync now". `syncTick` re-reads the timestamp
	// after a sync and on the 'ochorus:sync' event a merge/pull dispatches.
	let syncing = $state(false);
	let syncTick = $state(0);
	const lastSynced = $derived.by(() => {
		syncTick; // reactive dependency
		return readingSync.readLastSynced();
	});
	// Localised relative time ("just now", "3 minutes ago", "yesterday").
	const relSynced = $derived.by(() => {
		const ts = lastSynced;
		if (!ts) return t('settings.syncNever');
		const diffS = Math.round((ts - Date.now()) / 1000);
		if (Math.abs(diffS) < 45) return t('settings.syncJustNow');
		const rtf = new Intl.RelativeTimeFormat(lang.current, { numeric: 'auto' });
		const mins = Math.round(diffS / 60);
		if (Math.abs(mins) < 60) return rtf.format(mins, 'minute');
		const hrs = Math.round(diffS / 3600);
		if (Math.abs(hrs) < 24) return rtf.format(hrs, 'hour');
		return rtf.format(Math.round(diffS / 86400), 'day');
	});
	async function syncNow() {
		if (syncing) return;
		syncing = true;
		try {
			await readingSync.syncNow();
		} finally {
			syncing = false;
			syncTick += 1;
		}
	}
	onMount(() => {
		const bump = () => (syncTick += 1);
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	// The device's TTS voices load asynchronously; init the store so they populate,
	// then show only the best few for the currently-selected language.
	onMount(() => listen.init());
	const voices = $derived(listen.supported ? listen.topVoices(lang.current, 4) : []);
	// If the saved voice isn't among this language's picks, fall back to the first.
	const voiceValue = $derived(
		voices.some((v) => v.voiceURI === listen.voiceURI) ? listen.voiceURI : (voices[0]?.voiceURI ?? '')
	);
</script>

<svelte:head><title>{t('settings.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-8">
		<h1 class="text-display mb-2">{t('settings.title')}</h1>
		<p class="text-body text-muted">{t('settings.subtitle')}</p>
	</header>

	<div class="flex flex-col gap-6 sm:flex-row">
		<!-- Sidebar -->
		<nav class="flex shrink-0 gap-1 overflow-x-auto sm:w-48 sm:flex-col sm:overflow-visible" aria-label={t('settings.title')}>
			{#each SECTIONS as s (s.id)}
				<button
					class="flex items-center gap-2.5 whitespace-nowrap rounded-card px-4 py-2.5 text-small font-medium transition-colors"
					class:active-nav={section === s.id}
					class:text-muted={section !== s.id}
					aria-current={section === s.id ? 'page' : undefined}
					onclick={() => selectSection(s.id)}
				>
					<Icon name={s.icon} size={18} />{s.label}
				</button>
			{/each}
		</nav>

		<!-- Panel -->
		<section class="min-w-0 flex-1 rounded-card border border-border bg-surface p-6 sm:p-8">
			{#if section === 'profile'}
				<h2 class="text-h2 mb-1">{t('settings.profileTitle')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.profileSubtitle')}</p>
				{#if auth.user}
					<p class="text-body text-muted">
						{t('account.signedInAs')}
						<span class="font-semibold text-text">{auth.displayName || auth.user.email}</span>
					</p>
					{#if auth.displayName}
						<p class="text-small text-muted">{auth.user.email}</p>
					{/if}

					<!-- Display name -->
					<div class="mt-5">
						<label class="setting-label mb-1 block" for="displayName">{t('settings.displayName')}</label>
						<div class="flex flex-wrap items-center gap-2">
							<input
								id="displayName"
								class="settings-select !max-w-xs flex-1"
								bind:value={nameInput}
								oninput={() => (nameDirty = true)}
								placeholder={t('settings.displayNamePlaceholder')}
								maxlength="120"
								autocomplete="name"
							/>
							<button class="btn btn-ghost !py-1.5" disabled={nameSaving || !nameChanged} onclick={saveName}>
								{nameSaving ? t('settings.saving') : t('settings.save')}
							</button>
						</div>
					</div>

					<p class="mt-5 text-small text-muted">{t('settings.syncWhat')}</p>
					<div class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
						<span class="text-small text-muted">
							{t('settings.lastSynced')}: <span class="text-text">{relSynced}</span>
						</span>
						<button class="btn btn-ghost !py-1.5" disabled={syncing} onclick={syncNow}>
							{syncing ? t('settings.syncing') : t('settings.syncNow')}
						</button>
					</div>
					<button class="btn btn-ghost mt-5" onclick={() => auth.signOut()}>{t('account.signOut')}</button>
				{:else if auth.enabled}
					<p class="text-body text-muted">{t('account.signedOutNote')}</p>
				{:else}
					<p class="text-body text-muted">{t('account.localNote')}</p>
				{/if}

				<!-- Export my data — the reader's own devotional record, portable. -->
				<div class="mt-8 border-t border-border pt-6">
					<div class="setting-label">{t('settings.exportTitle')}</div>
					<div class="setting-sub mb-4">{t('settings.exportSub')}</div>
					<div class="flex flex-wrap gap-3">
						<button class="btn btn-ghost" disabled={!!exporting} onclick={() => exportData('md')}>
							{exporting === 'md' ? t('settings.exportBusy') : t('settings.exportMarkdown')}
						</button>
						<button class="btn btn-ghost" disabled={!!exporting} onclick={() => exportData('json')}>
							{exporting === 'json' ? t('settings.exportBusy') : t('settings.exportJson')}
						</button>
					</div>
				</div>
			{:else if section === 'reading'}
				<h2 class="text-h2 mb-1">{t('settings.navReading')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.readingSubtitle')}</p>

				<!-- Language -->
				{#if lang.available.length > 1}
					<div class="setting-row">
						<div>
							<div class="setting-label">{t('nav.language')}</div>
							<div class="setting-sub">{t('settings.languageSub')}</div>
						</div>
						<select
							class="settings-select"
							aria-label={t('nav.language')}
							value={lang.current}
							onchange={(e) => lang.choose((e.currentTarget as HTMLSelectElement).value)}
						>
							{#each lang.available as l (l.code)}
								<option value={l.code}>{l.native_name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<!-- Reading width -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('nav.readingWidth')}</div>
						<div class="setting-sub">{t('settings.readingWidthSub')}</div>
					</div>
					<div class="seg">
						{#each WIDTHS as w (w)}
							<button class:active={readerPrefs.measure === w} onclick={() => readerPrefs.setMeasure(w)}>
								{t(`settings.width_${w}`)}
							</button>
						{/each}
					</div>
				</div>

				<!-- Text size — mirrors the reader's Aa stepper (same readerPrefs.scale). -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.textSize')}</div>
						<div class="setting-sub">{t('settings.textSizeSub')}</div>
					</div>
					<div class="flex items-center gap-1">
						<button
							class="btn btn-ghost !px-2.5 !py-1"
							onclick={() => readerPrefs.bumpScale(-0.1)}
							aria-label={t('a11y.smallerText')}>A−</button
						>
						<span class="w-12 text-center text-small text-muted">{Math.round(readerPrefs.scale * 100)}%</span>
						<button
							class="btn btn-ghost !px-2.5 !py-1 !text-base"
							onclick={() => readerPrefs.bumpScale(0.1)}
							aria-label={t('a11y.largerText')}>A+</button
						>
					</div>
				</div>

				<!-- Default edition — carry the preference into the book page read CTAs. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.defaultEdition')}</div>
						<div class="setting-sub">{t('settings.defaultEditionSub')}</div>
					</div>
					<div class="seg">
						<button class:active={!readerPrefs.preferModern} onclick={() => readerPrefs.setPreferModern(false)}>
							{t('reader.original')}
						</button>
						<button class:active={readerPrefs.preferModern} onclick={() => readerPrefs.setPreferModern(true)}>
							{t('reader.modern')}
						</button>
					</div>
				</div>

				<!-- Listen: voice + speed -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.voice')}</div>
						<div class="setting-sub">{t('settings.voiceSub')}</div>
					</div>
					{#if !listen.supported}
						<span class="text-small text-muted">{t('settings.voiceUnsupported')}</span>
					{:else if voices.length}
						<div class="flex items-center gap-2">
							<select
								class="settings-select"
								aria-label={t('settings.voice')}
								value={voiceValue}
								onchange={(e) => listen.setVoice((e.currentTarget as HTMLSelectElement).value)}
							>
								{#each voices as v (v.voiceURI)}
									<option value={v.voiceURI}>{v.name}</option>
								{/each}
							</select>
							<button
								class="btn btn-ghost !px-3 !py-1.5"
								aria-label={t('settings.preview')}
								title={t('settings.preview')}
								onclick={() => listen.preview(t('settings.voiceSample'), voiceValue)}
							>
								▶
							</button>
						</div>
					{:else}
						<span class="text-small text-muted">{t('settings.voiceNone')}</span>
					{/if}
				</div>
				{#if listen.supported && voices.length}
					<div class="setting-row">
						<div>
							<div class="setting-label">{t('settings.speed')}</div>
							<div class="setting-sub">{t('settings.speedSub')}</div>
						</div>
						<div class="seg">
							{#each RATES as r (r)}
								<button class:active={listen.rate === r} onclick={() => listen.setRate(r)}>{r}×</button>
							{/each}
						</div>
					</div>
				{/if}
			{:else if section === 'appearance'}
				<h2 class="text-h2 mb-1">{t('settings.navAppearance')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.appearanceSubtitle')}</p>

				<!-- Theme — preference (not the resolved theme): 'System' follows the OS. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('nav.theme')}</div>
						<div class="setting-sub">{t('settings.themeSub')}</div>
					</div>
					<div class="seg">
						<button class:active={theme.preference === 'system'} onclick={() => theme.set('system')}>{t('settings.themeSystem')}</button>
						<button class:active={theme.preference === 'light'} onclick={() => theme.set('light')}>{t('settings.themeLight')}</button>
						<button class:active={theme.preference === 'sepia'} onclick={() => theme.set('sepia')}>{t('settings.themeSepia')}</button>
						<button class:active={theme.preference === 'dark'} onclick={() => theme.set('dark')}>{t('settings.themeDark')}</button>
					</div>
				</div>

				<!-- Reading font -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.font')}</div>
						<div class="setting-sub">{t('settings.fontSub')}</div>
					</div>
					<select
						class="settings-select"
						aria-label={t('settings.font')}
						value={readerPrefs.font}
						onchange={(e) => readerPrefs.setFont((e.currentTarget as HTMLSelectElement).value as ReaderFont)}
					>
						{#each FONTS as f (f.id)}
							<option value={f.id}>{f.label}</option>
						{/each}
					</select>
				</div>
				<p class="pt-1 text-lg text-text" style="font-family: {FONT_STACK[readerPrefs.font]}">
					{t('settings.fontSample')}
				</p>
			{/if}
		</section>
	</div>
</div>

<style>
	.active-nav {
		background: var(--color-accent-soft);
		color: var(--color-accent);
	}
	.setting-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.9rem 0;
		border-top: 1px solid var(--color-border);
	}
	.setting-row:first-of-type {
		border-top: none;
		padding-top: 0;
	}
	.setting-label {
		font-weight: 600;
		color: var(--color-text);
	}
	.setting-sub {
		font-size: 0.8rem;
		color: var(--color-muted);
		margin-top: 0.1rem;
	}
	.settings-select {
		border: 1px solid var(--color-border);
		background: var(--color-surface-2);
		color: var(--color-text);
		border-radius: 0.6rem;
		padding: 0.4rem 0.6rem;
		font-size: 0.9rem;
		max-width: 12rem;
	}
	.seg {
		display: inline-flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 0.15rem;
		background: var(--color-surface-2);
		border: 1px solid var(--color-border);
		border-radius: 999px;
		padding: 0.15rem;
	}
	.seg button {
		border-radius: 999px;
		padding: 0.3rem 0.75rem;
		font-size: 0.85rem;
		color: var(--color-muted);
		white-space: nowrap;
	}
	.seg button.active {
		background: var(--color-accent-soft);
		color: var(--color-accent);
		font-weight: 600;
	}
</style>
