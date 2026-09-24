import { HistoryItem, SavedQueryItem } from '../types';

const HISTORY_KEY = 'gst_sahayak_history';
const SAVED_QUERIES_KEY = 'gst_sahayak_saved_queries';

export function getHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (err) {
    console.error('Failed to parse history from localStorage', err);
    return [];
  }
}

export function saveHistoryItem(item: Omit<HistoryItem, 'id' | 'timestamp'>): HistoryItem {
  const history = getHistory();
  const newItem: HistoryItem = {
    ...item,
    id: `hist_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
    timestamp: new Date().toISOString(),
  };

  // Limit history to 50 items
  const updated = [newItem, ...history.filter(h => h.query !== item.query || h.mode !== item.mode)].slice(0, 50);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error('Failed to save history item to localStorage', err);
  }
  return newItem;
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch (err) {
    console.error('Failed to clear history from localStorage', err);
  }
}

export function deleteHistoryItem(id: string): HistoryItem[] {
  const history = getHistory();
  const updated = history.filter(item => item.id !== id);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error('Failed to delete history item from localStorage', err);
  }
  return updated;
}

export function getSavedQueries(): SavedQueryItem[] {
  try {
    const raw = localStorage.getItem(SAVED_QUERIES_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (err) {
    console.error('Failed to parse saved queries from localStorage', err);
    return [];
  }
}

export function toggleSaveQuery(
  query: string,
  mode: 'single' | 'multi' = 'single',
  financialYear?: string | null,
  asOfDate?: string | null,
  notes?: string
): { saved: boolean; items: SavedQueryItem[] } {
  const saved = getSavedQueries();
  const existingIndex = saved.findIndex(s => s.query.toLowerCase().trim() === query.toLowerCase().trim());

  let updated: SavedQueryItem[];
  let isSavedNow = false;

  if (existingIndex >= 0) {
    // Remove if already saved
    updated = saved.filter((_, idx) => idx !== existingIndex);
    isSavedNow = false;
  } else {
    // Add new saved query
    const newItem: SavedQueryItem = {
      id: `saved_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      query: query.trim(),
      savedAt: new Date().toISOString(),
      mode,
      financialYear,
      asOfDate,
      notes,
    };
    updated = [newItem, ...saved];
    isSavedNow = true;
  }

  try {
    localStorage.setItem(SAVED_QUERIES_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error('Failed to save query to localStorage', err);
  }

  return { saved: isSavedNow, items: updated };
}

export function isQuerySaved(query: string): boolean {
  if (!query) return false;
  const saved = getSavedQueries();
  return saved.some(s => s.query.toLowerCase().trim() === query.toLowerCase().trim());
}

export function deleteSavedQuery(id: string): SavedQueryItem[] {
  const saved = getSavedQueries();
  const updated = saved.filter(item => item.id !== id);
  try {
    localStorage.setItem(SAVED_QUERIES_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error('Failed to delete saved query from localStorage', err);
  }
  return updated;
}
