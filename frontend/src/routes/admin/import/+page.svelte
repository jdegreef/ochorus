<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, apiFetch, apiFetchRaw } from '$lib/api';
	import {
		createAuthor,
		listAuthors,
		listImportLanguages,
		type AuthorBio,
		type Language
	} from '$lib/library';

	type Chapter = { title: string; html: string; words: number };
	type Warning = {
		check: string;
		severity: 'high' | 'medium' | 'low';
		chapter_index: number | null;
		title: string;
		message: string;
	};
	type Preview = {
		kind: 'book' | 'sermon';
		chapters: Chapter[];
		suggested_title: string;
		warnings: Warning[];
	};
	type Published = { kind: string; slug: string; title: string; path: string; chapters?: number };

	let authors = $state<AuthorBio[]>([]);
	let languages = $state<Language[]>([{ code: 'en', name: 'English', native_name: 'English' }]);

	let kind = $state<'book' | 'sermon'>('book');
	let authorSlug = $state('');
	let language = $state('en');
	let file = $state<File | null>(null);

	let preview = $state<Preview | null>(null);
	let title = $state('');
	let scriptureRef = $state('');
	let sourceUrl = $state('');

	// Optional book metadata, captured at import instead of a separate edit later.
	let subtitle = $state('');
	let coverColor = $state('');
	let coverUrl = $state('');
	let publicationYear = $state('');
	let attribution = $state('');

	// Inline "New author…" — create a stub without leaving the page.
	let addingAuthor = $state(false);
	let newAuthorName = $state('');

	let busy = $state(false);
	let error = $state<string | null>(null);
	let published = $state<Published | null>(null);

	onMount(async () => {
		try {
			[authors, languages] = await Promise.all([
				listAuthors(),
				listImportLanguages().catch(() => languages)
			]);
		} catch {
			/* leave defaults */
		}
	});

	function pickFile(e: Event) {
		file = (e.target as HTMLInputElement).files?.[0] ?? null;
	}

	async function addAuthor() {
		const name = newAuthorName.trim();
		if (!name || busy) return; // in-flight guard: a held/double Enter must not double-create
		busy = true;
		error = null;
		try {
			const a = await createAuthor(name);
			authors = [...authors, a].sort((x, y) => x.name.localeCompare(y.name));
			authorSlug = a.slug;
			addingAuthor = false;
			newAuthorName = '';
		} catch (e) {
			error = errMsg(e, 'Could not add the author.');
		} finally {
			busy = false;
		}
	}

	function errMsg(e: unknown, fallback: string): string {
		if (e instanceof ApiError) {
			const b = e.body as { detail?: string } | string | null;
			if (b && typeof b === 'object' && b.detail) return b.detail;
			if (typeof b === 'string' && b) return b;
		}
		return fallback;
	}

	async function parse() {
		if (!file) {
			error = 'Choose a Word or PDF file first.';
			return;
		}
		busy = true;
		error = null;
		try {
			const form = new FormData();
			form.append('file', file);
			form.append('kind', kind);
			const res = await apiFetchRaw('/api/admin/import/parse/', { method: 'POST', body: form });
			const data: Preview = await res.json();
			preview = data;
			title = data.suggested_title || title;
		} catch (e) {
			error = errMsg(e, 'Could not read that document.');
		} finally {
			busy = false;
		}
	}

	function removeChapter(i: number) {
		if (!preview) return;
		preview.chapters = preview.chapters.filter((_, idx) => idx !== i);
		// Keep the warning "Ch N" references aligned: drop the removed chapter's
		// warnings and shift indices above it down by one.
		preview.warnings = (preview.warnings ?? [])
			.filter((w) => w.chapter_index !== i)
			.map((w) =>
				w.chapter_index !== null && w.chapter_index > i
					? { ...w, chapter_index: w.chapter_index - 1 }
					: w
			);
	}

	async function publish() {
		if (!preview) return;
		if (!authorSlug) {
			error = 'Pick the author.';
			return;
		}
		if (!title.trim()) {
			error = 'Enter a title.';
			return;
		}
		busy = true;
		error = null;
		try {
			const base = { author_slug: authorSlug, title, language, source_url: sourceUrl };
			const payload =
				preview.kind === 'book'
					? {
							...base,
							kind: 'book',
							subtitle,
							cover_color: coverColor,
							cover_url: coverUrl,
							publication_year: publicationYear,
							attribution,
							chapters: preview.chapters.map((c) => ({ title: c.title, html: c.html }))
						}
					: {
							...base,
							kind: 'sermon',
							scripture_ref: scriptureRef,
							body_html: preview.chapters[0]?.html ?? ''
						};
			published = await apiFetch<Published>('/api/admin/import/publish/', {
				method: 'POST',
				body: JSON.stringify(payload)
			});
		} catch (e) {
			error = errMsg(e, 'Could not publish.');
		} finally {
			busy = false;
		}
	}

	function reset() {
		preview = null;
		published = null;
		file = null;
		title = '';
		scriptureRef = '';
		sourceUrl = '';
		subtitle = '';
		coverColor = '';
		coverUrl = '';
		publicationYear = '';
		attribution = '';
		error = null;
	}

	const totalWords = $derived(preview?.chapters.reduce((n, c) => n + c.words, 0) ?? 0);
	const plainText = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
</script>

<svelte:head><title>Import a document — Ochorus Admin</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-8">
	<h1 class="text-h2">Import a document</h1>
	<p class="mt-1 text-body text-muted">
		Upload a Word (.docx) or text PDF of a book or sermon, choose its author, and Ochorus will
		parse it into content. Review the result before publishing.
	</p>

	{#if published}
		<!-- Success -->
		<div class="mt-8 rounded-card border border-border bg-surface p-6 text-center">
			<div class="mail-badge mx-auto mb-3">✓</div>
			<h2 class="text-h3 mb-1">Published</h2>
			<p class="mb-4 text-body text-muted">
				“{published.title}” is live{#if published.chapters}
					· {published.chapters} {published.chapters === 1 ? 'chapter' : 'chapters'}{/if}.
			</p>
			<div class="flex flex-wrap justify-center gap-3">
				<a class="btn btn-primary" href={published.path}>View it</a>
				<button class="btn btn-ghost" onclick={reset}>Import another</button>
			</div>
		</div>
	{:else if !preview}
		<!-- Step 1: upload form -->
		<div class="mt-6 rounded-card border border-border bg-surface p-6">
			<fieldset class="mb-4">
				<legend class="mb-2 text-small font-semibold text-text">Type</legend>
				<div class="flex gap-2">
					<label class="typechip" class:on={kind === 'book'}>
						<input type="radio" bind:group={kind} value="book" class="sr-only" /> Book
					</label>
					<label class="typechip" class:on={kind === 'sermon'}>
						<input type="radio" bind:group={kind} value="sermon" class="sr-only" /> Sermon
					</label>
				</div>
			</fieldset>

			<div class="mb-1 flex items-center justify-between">
				<label class="text-small font-semibold text-text" for="author">Author</label>
				<button
					type="button"
					class="text-small font-semibold text-accent hover:underline"
					onclick={() => {
						addingAuthor = !addingAuthor;
						error = null;
					}}
				>
					{addingAuthor ? 'Pick existing' : '+ New author'}
				</button>
			</div>
			{#if addingAuthor}
				<div class="mb-4 flex gap-2">
					<!-- svelte-ignore a11y_autofocus -->
					<input
						bind:value={newAuthorName}
						placeholder="Author's full name"
						autofocus
						disabled={busy}
						onkeydown={(e) => e.key === 'Enter' && addAuthor()}
						class="min-w-0 flex-1 rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
					/>
					<button
						class="btn btn-primary shrink-0"
						onclick={addAuthor}
						disabled={busy || !newAuthorName.trim()}>Add</button
					>
				</div>
			{:else}
				<select
					id="author"
					bind:value={authorSlug}
					class="mb-4 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
				>
					<option value="" disabled>Choose the author…</option>
					{#each authors as a (a.slug)}
						<option value={a.slug}>{a.name}</option>
					{/each}
				</select>
			{/if}

			<label class="mb-1 block text-small font-semibold text-text" for="lang">Language</label>
			<select
				id="lang"
				bind:value={language}
				class="mb-4 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
			>
				{#each languages as l (l.code)}
					<option value={l.code}>{l.name}</option>
				{/each}
			</select>

			<label class="mb-1 block text-small font-semibold text-text" for="file">Document</label>
			<input
				id="file"
				type="file"
				accept=".pdf,.docx"
				onchange={pickFile}
				class="mb-4 block w-full text-small text-muted file:mr-3 file:rounded-sm file:border file:border-border file:bg-surface-2 file:px-3 file:py-1.5 file:text-text"
			/>

			{#if error}<p class="mb-3 text-small text-danger">{error}</p>{/if}

			<button class="btn btn-primary" onclick={parse} disabled={busy || !file || !authorSlug}>
				{busy ? 'Reading…' : 'Read document'}
			</button>
			<p class="mt-3 text-small text-muted">
				Scanned image PDFs aren't supported yet — use a text PDF or Word document.
			</p>
		</div>
	{:else}
		<!-- Step 2: review & publish -->
		<div class="mt-6 rounded-card border border-border bg-surface p-6">
			<div class="mb-4 flex items-center justify-between">
				<span class="eyebrow text-accent">
					Review {preview.kind}
				</span>
				<span class="text-small text-muted">
					{#if preview.kind === 'book'}{preview.chapters.length} chapters ·
					{/if}{totalWords.toLocaleString()} words
				</span>
			</div>

			{#if preview.warnings?.length}
				<!-- Content-quality heads-up on the parsed file (advisory, not blocking).
				     A parse-time snapshot: it doesn't re-run as you edit the fields below. -->
				<div class="mb-4 rounded-sm border border-border bg-bg p-3">
					<p class="mb-2 text-small font-semibold text-text">
						From the imported file · {preview.warnings.length}
						{preview.warnings.length === 1 ? 'thing' : 'things'} worth a look
					</p>
					<ul class="space-y-1.5">
						{#each preview.warnings as w (w.check + '-' + (w.chapter_index ?? 'book'))}
							<li class="flex gap-2 text-small">
								<span class="qa-dot qa-{w.severity}" title={w.severity} aria-hidden="true"></span>
								<span class="text-muted">
									{#if w.chapter_index !== null}<span class="font-semibold text-text"
											>Ch {w.chapter_index + 1}{#if w.title} · {w.title}{/if}:</span
										>
									{/if}{w.message}
								</span>
							</li>
						{/each}
					</ul>
					<p class="mt-2 text-micro text-muted">
						Fix the titles below, or publish as-is.
					</p>
				</div>
			{/if}

			<label class="mb-1 block text-small font-semibold text-text" for="title">Title</label>
			<input
				id="title"
				bind:value={title}
				placeholder="Title"
				class="mb-4 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
			/>

			{#if preview.kind === 'sermon'}
				<label class="mb-1 block text-small font-semibold text-text" for="ref">
					Scripture reference <span class="font-normal text-muted">(optional)</span>
				</label>
				<input
					id="ref"
					bind:value={scriptureRef}
					placeholder="e.g. John 3:16"
					class="mb-4 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
				/>
				<p class="rounded-sm border border-border bg-bg p-3 text-small text-muted">
					{plainText(preview.chapters[0]?.html ?? '').slice(0, 400)}…
				</p>
			{:else}
				<p class="mb-2 text-small font-semibold text-text">Chapters</p>
				<ol class="space-y-2">
					{#each preview.chapters as ch, i (i)}
						<li class="flex items-center gap-2 rounded-sm border border-border bg-bg p-2">
							<span class="w-6 shrink-0 text-center text-small text-muted">{i + 1}</span>
							<input
								bind:value={ch.title}
								placeholder="Chapter title"
								class="min-w-0 flex-1 rounded-sm border border-border bg-surface px-2 py-1 text-small text-text"
							/>
							<span class="shrink-0 text-small text-muted">{ch.words}w</span>
							<button
								class="shrink-0 rounded-sm px-2 py-1 text-small text-muted hover:text-danger"
								onclick={() => removeChapter(i)}
								aria-label="Remove chapter"
								title="Remove chapter">✕</button
							>
						</li>
					{/each}
				</ol>
				{#if preview.chapters.length === 1}
					<p class="mt-2 text-small text-muted">
						Only one chapter detected — if this book has more, its source may not mark chapter
						breaks in a way the parser recognises.
					</p>
				{/if}

				<!-- Optional book metadata, captured here instead of a later edit. -->
				<div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
					<div>
						<label class="mb-1 block text-small font-semibold text-text" for="subtitle">
							Subtitle <span class="font-normal text-muted">(optional)</span>
						</label>
						<input id="subtitle" bind:value={subtitle} placeholder="Subtitle" class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text" />
					</div>
					<div>
						<label class="mb-1 block text-small font-semibold text-text" for="pubyear">
							First published <span class="font-normal text-muted">(year)</span>
						</label>
						<input
							id="pubyear"
							type="number"
							min="1"
							max="2100"
							bind:value={publicationYear}
							placeholder="e.g. 1885"
							class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
						/>
					</div>
					<div>
						<label class="mb-1 block text-small font-semibold text-text" for="cover">
							Cover accent <span class="font-normal text-muted">(no image)</span>
						</label>
						<div class="flex gap-2">
							<input
								id="cover"
								type="color"
								bind:value={coverColor}
								aria-label="Cover accent colour"
								class="h-9 w-12 shrink-0 rounded-sm border border-border bg-bg"
							/>
							<input
							bind:value={coverColor}
							placeholder="#3b5bdb"
							class="min-w-0 flex-1 rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
						/>
						</div>
					</div>
					<div>
						<label class="mb-1 block text-small font-semibold text-text" for="coverurl">
							Cover image URL <span class="font-normal text-muted">(optional)</span>
						</label>
						<input id="coverurl" bind:value={coverUrl} placeholder="https://…" class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text" />
					</div>
				</div>
				<label class="mb-1 mt-3 block text-small font-semibold text-text" for="attr">
					Attribution / licence note <span class="font-normal text-muted">(optional)</span>
				</label>
				<textarea
					id="attr"
					bind:value={attribution}
					rows="2"
					placeholder="e.g. Public domain — scanned by CCEL"
					class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
				></textarea>
			{/if}

			<label class="mb-1 mt-4 block text-small font-semibold text-text" for="src">
				Source URL <span class="font-normal text-muted">(optional)</span>
			</label>
			<input
				id="src"
				bind:value={sourceUrl}
				placeholder="https://…"
				class="mb-4 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
			/>

			{#if error}<p class="mb-3 text-small text-danger">{error}</p>{/if}

			<div class="flex flex-wrap gap-3">
				<button
					class="btn btn-primary"
					onclick={publish}
					disabled={busy || (preview.kind === 'book' && preview.chapters.length === 0)}
				>
					{busy ? 'Publishing…' : `Publish ${preview.kind}`}
				</button>
				<button class="btn btn-ghost" onclick={reset} disabled={busy}>Start over</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.typechip {
		cursor: pointer;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		padding: 0.4rem 1rem;
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
	}
	.typechip.on {
		border-color: var(--accent-soft-border);
		background: var(--accent-soft);
		color: var(--accent);
	}
	.mail-badge {
		display: flex;
		height: 3rem;
		width: 3rem;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		font-size: var(--fs-h3);
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 15%, transparent);
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
	.qa-dot {
		margin-top: 0.42rem;
		height: 0.5rem;
		width: 0.5rem;
		flex-shrink: 0;
		border-radius: 999px;
		background: var(--muted);
	}
	.qa-high {
		background: var(--danger);
	}
	.qa-medium {
		background: var(--accent);
	}
	.qa-low {
		background: color-mix(in srgb, var(--muted) 60%, transparent);
	}
</style>
