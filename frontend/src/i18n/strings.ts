export type Lang = 'en' | 'de'

export const LANGS: { code: Lang; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
]

// Flat key → per-language string. Keep keys short and namespaced by screen.
export const STRINGS = {
  'app.name': { en: 'BuyBot', de: 'BuyBot' },
  'common.continue': { en: 'Continue', de: 'Weiter' },
  'common.cancel': { en: 'Cancel', de: 'Abbrechen' },
  'common.back': { en: 'Back', de: 'Zurück' },
  'common.loading': { en: 'Loading…', de: 'Lädt…' },
  // Input screen
  'input.heading': { en: 'What should I find for you?', de: 'Was soll ich für dich finden?' },
  'input.item': { en: 'The item', de: 'Der Artikel' },
  'input.budget': { en: 'Budget range', de: 'Budgetbereich' },
  'input.condition': { en: 'Minimum condition', de: 'Mindestzustand' },
  'input.city': { en: 'Your city', de: 'Deine Stadt' },
  'input.submit': { en: 'Find the best deal', de: 'Bestes Angebot finden' },
  // Settings
  'settings.title': { en: 'Settings', de: 'Einstellungen' },
  'settings.language': { en: 'Language', de: 'Sprache' },
  'settings.defaultAddress': { en: 'Default address', de: 'Standardadresse' },
  'settings.save': { en: 'Save', de: 'Speichern' },
  // Auth
  'auth.login': { en: 'Log in', de: 'Anmelden' },
  'auth.signup': { en: 'Sign up', de: 'Registrieren' },
  'auth.email': { en: 'Email', de: 'E-Mail' },
  'auth.password': { en: 'Password', de: 'Passwort' },
  'auth.name': { en: 'Name', de: 'Name' },
  'auth.google': { en: 'Continue with Google', de: 'Mit Google fortfahren' },
  // Negotiation / translation affordance
  'msg.showTranslation': { en: 'Show translation', de: 'Übersetzung anzeigen' },
} as const

export type StringKey = keyof typeof STRINGS
