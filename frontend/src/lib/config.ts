import { PUBLIC_API_BASE_URL } from '$env/static/public';

// Base URL of the Django API. Empty string = same origin (production, where the
// API is served from the same host). In dev, set PUBLIC_API_BASE_URL to the
// local backend (see .env).
export const API_BASE_URL = PUBLIC_API_BASE_URL || '';
