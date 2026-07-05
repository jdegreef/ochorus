import { apiFetch } from './api';

export interface Author {
	slug: string;
	name: string;
	bio: string;
	birth_year: number | null;
	death_year: number | null;
}

export type SourceType = 'public_domain' | 'ai_reviewed' | 'ai_unreviewed';

export interface BookSummary {
	slug: string;
	language: string;
	title: string;
	subtitle: string;
	author: Author;
	source_type: SourceType;
	cover_color: string;
	cover_url: string;
	chapter_count: number;
}

export interface ChapterToc {
	order: number;
	title: string;
	word_count: number;
}

export interface BookDetail extends BookSummary {
	description: string;
	source_url: string;
	pdf_url: string;
	chapters: ChapterToc[];
}

export interface ChapterNav {
	order: number;
	title: string;
}

export interface Chapter {
	order: number;
	title: string;
	body_html: string;
	word_count: number;
	book_title: string;
	book_slug: string;
	author_name: string;
	author_slug: string;
	prev: ChapterNav | null;
	next: ChapterNav | null;
}

export interface Language {
	code: string;
	name: string;
	native_name: string;
}

export interface SearchHit {
	book_slug: string;
	book_title: string;
	author_name: string;
	chapter_order: number;
	chapter_title: string;
	snippet: string;
}

export interface SearchResponse {
	query: string;
	results: SearchHit[];
}

export interface AuthorBio {
	slug: string;
	name: string;
	bio: string;
	birth_year: number | null;
	death_year: number | null;
	book_count: number;
}

export const listBooks = (language = 'en') =>
	apiFetch<BookSummary[]>(`/api/library/books/?language=${language}`);

export const listAuthors = () => apiFetch<AuthorBio[]>('/api/library/authors/');

export const getBook = (slug: string, language = 'en') =>
	apiFetch<BookDetail>(`/api/library/books/${slug}/?language=${language}`);

export const getChapter = (slug: string, order: number, language = 'en') =>
	apiFetch<Chapter>(`/api/library/books/${slug}/chapters/${order}/?language=${language}`);

export const listLanguages = () => apiFetch<Language[]>('/api/library/languages/');

export const search = (q: string, language = 'en') =>
	apiFetch<SearchResponse>(
		`/api/library/search/?q=${encodeURIComponent(q)}&language=${language}`
	);

export interface PlanSummary {
	slug: string;
	language: string;
	title: string;
	description: string;
	day_count: number;
}

export interface PlanDay {
	day: number;
	book_slug: string;
	chapter_order: number;
	book_title: string;
	chapter_title: string;
}

export interface PlanDetail extends PlanSummary {
	days: PlanDay[];
}

export const listPlans = (language = 'en') =>
	apiFetch<PlanSummary[]>(`/api/library/plans/?language=${language}`);

export const getPlan = (slug: string, language = 'en') =>
	apiFetch<PlanDetail>(`/api/library/plans/${slug}/?language=${language}`);
