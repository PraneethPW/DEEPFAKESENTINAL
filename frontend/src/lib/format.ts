export const percent = (value?: number) => value == null ? '—' : `${Math.round(value * 100)}%`;
export const bytes = (value: number) => value < 1024 ** 2 ? `${Math.max(1, Math.round(value / 1024))} KB` : `${(value / 1024 ** 2).toFixed(1)} MB`;
export const dateTime = (value?: string) => value ? new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : '—';
export const label = (value?: string) => value ? value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Unavailable';

