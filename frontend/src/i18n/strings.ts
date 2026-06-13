export type Lang = 'en' | 'de' | 'zh'

export const LANGS: { code: Lang; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
  { code: 'zh', label: '繁體中文' },
]

// Flat key → per-language string. Keep keys short and namespaced by screen.
export const STRINGS = {
  'app.name': { en: 'BuyBot', de: 'BuyBot', zh: 'BuyBot' },
  'common.continue': { en: 'Continue', de: 'Weiter', zh: '繼續' },
  'common.cancel': { en: 'Cancel', de: 'Abbrechen', zh: '取消' },
  'common.back': { en: 'Back', de: 'Zurück', zh: '返回' },
  'common.loading': { en: 'Loading…', de: 'Lädt…', zh: '載入中…' },
  // Input screen
  'input.heading': { en: 'What should I find for you?', de: 'Was soll ich für dich finden?', zh: '想找什麼？讓我幫你' },
  'input.item': { en: 'The item', de: 'Der Artikel', zh: '物品' },
  'input.budget': { en: 'Budget range', de: 'Budgetbereich', zh: '預算範圍' },
  'input.condition': { en: 'Minimum condition', de: 'Mindestzustand', zh: '最低狀態' },
  'input.city': { en: 'Your city', de: 'Deine Stadt', zh: '你的城市' },
  'input.submit': { en: 'Find the best deal', de: 'Bestes Angebot finden', zh: '幫我找最划算的' },
  // Settings
  'settings.title': { en: 'Settings', de: 'Einstellungen', zh: '設定' },
  'settings.language': { en: 'Language', de: 'Sprache', zh: '語言' },
  'settings.defaultAddress': { en: 'Default address', de: 'Standardadresse', zh: '預設地址' },
  'settings.save': { en: 'Save', de: 'Speichern', zh: '儲存' },
  // Auth
  'auth.login': { en: 'Log in', de: 'Anmelden', zh: '登入' },
  'auth.signup': { en: 'Sign up', de: 'Registrieren', zh: '註冊' },
  'auth.email': { en: 'Email', de: 'E-Mail', zh: '電子郵件' },
  'auth.password': { en: 'Password', de: 'Passwort', zh: '密碼' },
  'auth.name': { en: 'Name', de: 'Name', zh: '名稱' },
  // Negotiation / translation affordance
  'msg.showTranslation': { en: 'Show translation', de: 'Übersetzung anzeigen', zh: '顯示翻譯' },
} as const

export type StringKey = keyof typeof STRINGS
