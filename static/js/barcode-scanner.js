(function () {
  const SCRIPT_URL = '/static/js/html5-qrcode.min.js';
  let loadPromise = null;

  function loadLibrary() {
    console.log('[ProcessNovaScanner] Cargando biblioteca...');
    if (window.Html5Qrcode) {
      console.log('[ProcessNovaScanner] Biblioteca ya está cargada');
      return Promise.resolve();
    }
    if (loadPromise) {
      console.log('[ProcessNovaScanner] Biblioteca ya está cargándose...');
      return loadPromise;
    }
    loadPromise = new Promise(function (resolve, reject) {
      const existing = document.querySelector('script[data-processnova-scanner="1"]');
      if (existing) {
        console.log('[ProcessNovaScanner] Script ya está agregado, esperando a que cargue');
        existing.addEventListener('load', function () { 
          console.log('[ProcessNovaScanner] Script cargado (existing)');
          resolve(); 
        });
        existing.addEventListener('error', function (e) { 
          console.error('[ProcessNovaScanner] Error al cargar script (existing)', e);
          reject(new Error('No se pudo cargar el escáner')); 
        });
        return;
      }
      console.log('[ProcessNovaScanner] Agregando script al DOM desde:', SCRIPT_URL);
      const script = document.createElement('script');
      script.src = SCRIPT_URL;
      script.async = true;
      script.dataset.processnovaScanner = '1';
      script.onload = function () { 
        console.log('[ProcessNovaScanner] Script cargado exitosamente');
        resolve(); 
      };
      script.onerror = function (e) { 
        console.error('[ProcessNovaScanner] Error al cargar el script:', e);
        reject(new Error('No se pudo cargar el escáner (error en la carga del script)')); 
      };
      document.head.appendChild(script);
    });
    return loadPromise;
  }

  function barcodeFormats() {
    const formats = window.Html5QrcodeSupportedFormats;
    if (!formats) {
      return null;
    }
    return [
      formats.QR_CODE,
      formats.EAN_13,
      formats.EAN_8,
      formats.UPC_A,
      formats.UPC_E,
      formats.CODE_128,
      formats.CODE_39,
      formats.ITF,
    ];
  }

  async function start(elementId, onSuccess, options) {
    options = options || {};
    console.log('[ProcessNovaScanner] Iniciando escáner en elemento:', elementId);
    try {
      await loadLibrary();
      console.log('[ProcessNovaScanner] Biblioteca cargada, creando instancia Html5Qrcode');
      const scanner = new Html5Qrcode(elementId);
      const config = {
        fps: options.fps || 10,
        qrbox: options.qrbox || { width: 280, height: 140 },
        aspectRatio: options.aspectRatio || 1.777778,
      };
      const formats = barcodeFormats();
      if (formats) {
        config.formatsToSupport = formats;
      }
      console.log('[ProcessNovaScanner] Configuración del escáner:', config);
      console.log('[ProcessNovaScanner] Solicitando acceso a la cámara...');
      await scanner.start({ facingMode: 'environment' }, config, onSuccess);
      console.log('[ProcessNovaScanner] Escáner iniciado correctamente');
      return scanner;
    } catch (error) {
      console.error('[ProcessNovaScanner] Error al iniciar el escáner:', error);
      throw error;
    }
  }

  async function stop(scanner) {
    if (!scanner) {
      return;
    }
    console.log('[ProcessNovaScanner] Deteniendo escáner...');
    try {
      await scanner.stop();
      console.log('[ProcessNovaScanner] Escáner detenido');
    } catch (error) {
      console.warn('[ProcessNovaScanner] Error al detener escáner (puede que ya estuviera detenido):', error);
    }
    try {
      await scanner.clear();
    } catch (error) {
      console.warn('[ProcessNovaScanner] Error al limpiar escáner:', error);
    }
  }

  window.ProcessNovaScanner = {
    loadLibrary: loadLibrary,
    start: start,
    stop: stop,
  };
})();
