/**
 * `t()` serves the UI catalogue its document loaded before rendering
 * ($lib/i18n: the client and server hooks do the loading). A test has no hook,
 * so load every locale's catalogue here, before any test file runs — a test
 * that switches locale finds its strings just as one in English does.
 */
import { loadUiCatalog } from '$lib/i18n.svelte';
import settings from '../../project.inlang/settings.json';

await Promise.all(settings.locales.map(loadUiCatalog));
