/**
 * The media queries script decides things on, so a component can't drift from
 * the stylesheet by retyping one. They mirror app.css's breakpoints:
 * `max-width: 639.98px` is "below Tailwind's sm", and a SHORT_TOUCH screen is
 * a phone held sideways (no tablet is under 500px tall).
 */
export const PHONE = '(max-width: 639.98px)';
export const SHORT_TOUCH = '(max-height: 499.98px) and (pointer: coarse)';
