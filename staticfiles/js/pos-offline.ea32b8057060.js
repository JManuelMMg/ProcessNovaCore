const DB_NAME = 'processnova-pos';
const DB_VERSION = 1;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('products')) {
        db.createObjectStore('products', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('pendingSales')) {
        db.createObjectStore('pendingSales', { keyPath: 'offline_id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function cacheProducts(products) {
  const db = await openDB();
  const tx = db.transaction('products', 'readwrite');
  const store = tx.objectStore('products');
  store.clear();
  products.forEach((p) => store.put(p));
  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function getCachedProducts() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('products', 'readonly');
    const req = tx.objectStore('products').getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function queueOfflineSale(saleData) {
  const db = await openDB();
  saleData.offline_id = `offline_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  saleData.created_at = new Date().toISOString();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingSales', 'readwrite');
    const req = tx.objectStore('pendingSales').add(saleData);
    req.onsuccess = () => resolve(saleData.offline_id);
    req.onerror = () => reject(req.error);
  });
}

async function getPendingSales() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingSales', 'readonly');
    const req = tx.objectStore('pendingSales').getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function removePendingSale(offlineId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingSales', 'readwrite');
    tx.objectStore('pendingSales').delete(offlineId);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function fetchAndCacheProducts(csrfToken) {
  const res = await fetch('/sales/api/products-cache/', {
    headers: { 'X-CSRFToken': csrfToken },
  });
  if (!res.ok) return [];
  const data = await res.json();
  await cacheProducts(data.products);
  return data.products;
}

async function syncPendingSales(csrfToken) {
  const pending = await getPendingSales();
  if (!pending.length) return { synced: 0 };
  const res = await fetch('/sales/api/sync-offline/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ sales: pending }),
  });
  const data = await res.json();
  for (const result of data.results) {
    if (result.success) {
      await removePendingSale(result.offline_id);
    }
  }
  return data;
}

function updateOnlineStatus() {
  const el = document.getElementById('offline-status');
  if (!el) return;
  if (navigator.onLine) {
    el.textContent = '● En línea';
    el.className = 'text-xs px-2 py-1 rounded-full bg-green-100 text-green-800';
  } else {
    el.textContent = '● Sin conexión — modo offline';
    el.className = 'text-xs px-2 py-1 rounded-full bg-yellow-100 text-yellow-800';
  }
}

window.PosOffline = {
  openDB,
  cacheProducts,
  getCachedProducts,
  queueOfflineSale,
  getPendingSales,
  fetchAndCacheProducts,
  syncPendingSales,
  updateOnlineStatus,
};
