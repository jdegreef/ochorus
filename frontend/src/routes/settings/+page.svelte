<script lang="ts">
	import { onMount } from 'svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { theme } from '$lib/theme.svelte';
	import { lang } from '$lib/lang.svelte';
	import { readerPrefs, FONT_STACK, MEASURE, type ReaderFont, type Measure } from '$lib/readerPrefs.svelte';
	import { listen, RATES } from '$lib/listen.svelte';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	const t = i18n.t;

	type Section = 'profile' | 'reading' | 'appearance';
	const SECTIONS: { id: Section; label: string; icon: IconName }[] = [
		{ id: 'profile', label: t('settings.navProfile'), icon: 'users' },
		{ id: 'reading', label: t('settings.navReading'), icon: 'book' },
		{ id: 'appearance', label: t('settings.navAppearance'), icon: 'sun' }
	];
	let section = $state<Section>('profile');

	const FONTS: { id: ReaderFont; label: string }[] = [
		{ id: 'serif', label: t('settings.fontSerif') },
		{ id: 'sans', label: t('settings.fontSans') },
		{ id: 'dyslexic', label: t('settings.fontDyslexic') }
	];
	const WIDTHS = Object.keys(MEASURE) as Measure[];

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
					onclick={() => (section = s.id)}
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
						<span class="font-semibold text-text">{auth.user.email}</span>
					</p>
					<p class="mt-1 text-small text-muted">{t('account.syncNote')}</p>
					<button class="btn btn-ghost mt-5" onclick={() => auth.signOut()}>{t('account.signOut')}</button>
				{:else if auth.enabled}
					<p class="text-body text-muted">{t('account.signedOutNote')}</p>
				{:else}
					<p class="text-body text-muted">{t('account.localNote')}</p>
				{/if}
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
							value={lang.current}
							onchange={(e) => lang.set((e.currentTarget as HTMLSelectElement).value)}
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

				<!-- Theme -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('nav.theme')}</div>
						<div class="setting-sub">{t('settings.themeSub')}</div>
					</div>
					<div class="seg">
						<button class:active={theme.current === 'light'} onclick={() => theme.set('light')}>{t('settings.themeLight')}</button>
						<button class:active={theme.current === 'dark'} onclick={() => theme.set('dark')}>{t('settings.themeDark')}</button>
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
