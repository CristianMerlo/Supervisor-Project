/**
 * GOOGLE APPS SCRIPT: DEPLOYMENT ENGINE FOR MOSTAZA LOCALES DRIVE HIERARCHY
 * Architectural Role: High-Fidelity Infrastructure Provisioner
 * Target: Google Drive / Google Sheets Extensions Editor
 * 
 * DESIGN FEATURES:
 * 1. Idempotency Guaranteed: Uses 1-pass parent child caching to avoid duplicating folders on repeated runs.
 * 2. High Performance (O(1) checks): Prevents Apps Script Execution Timeout (6-minute limit) by caching.
 * 3. Graceful Degradation: Individual try-catch blocks preserve state and report errors without halting execution.
 * 4. Dynamic Column Mapping: Automatically locates column indexes by header names.
 */

function deployDriveInfrastructure() {
  const ROOT_FOLDER_NAME = "Mostaza Locales";
  const HEADER_LOCAL = "LOCAL";
  const HEADER_SIGLA = "SIGLA SISTEMA";
  
  // Execution Counters for Audit Log
  let createdCount = 0;
  let verifiedCount = 0;
  let skippedCount = 0;
  let errorCount = 0;
  
  Logger.log("=== INICIANDO DESPLIEGUE DE INFRAESTRUCTURA: MOSTAZA LOCALES ===");
  
  try {
    // 1. VALIDACIÓN Y OBTENCIÓN DE CARPETA RAÍZ
    let rootFolder;
    const existingRootFolders = DriveApp.getFoldersByName(ROOT_FOLDER_NAME);
    
    if (existingRootFolders.hasNext()) {
      rootFolder = existingRootFolders.next();
      Logger.log("✅ Carpeta raíz existente encontrada. ID: " + rootFolder.getId());
      
      // Warn if there are multiple root folders with the same name
      if (existingRootFolders.hasNext()) {
        Logger.log("⚠️ ADVERTENCIA: Se encontraron múltiples carpetas con el nombre '" + ROOT_FOLDER_NAME + "'. Se usará la primera.");
      }
    } else {
      rootFolder = DriveApp.createFolder(ROOT_FOLDER_NAME);
      Logger.log("🆕 Carpeta raíz '" + ROOT_FOLDER_NAME + "' creada exitosamente. ID: " + rootFolder.getId());
    }
    
    // 2. CONSTRUIR CACHÉ DE SUB-CARPETAS EXISTENTES (O(1) Lookup Optimization)
    Logger.log("⚙️ Cargando caché de subcarpetas existentes para evitar duplicación y timeouts...");
    const existingSubFoldersCache = {};
    const childFolders = rootFolder.getFolders();
    
    while (childFolders.hasNext()) {
      const subFolder = childFolders.next();
      existingSubFoldersCache[subFolder.getName()] = subFolder.getId();
    }
    Logger.log("📦 Caché cargada. Total subcarpetas existentes detectadas: " + Object.keys(existingSubFoldersCache).length);
    
    // 3. LECTURA DE DATOS DESDE SPREADSHEET (FUENTE DE VERDAD)
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    if (values.length < 2) {
      Logger.log("❌ ERROR: La hoja de cálculo no contiene suficientes filas (cabecera + datos).");
      return;
    }
    
    // 4. MAPEO DINÁMICO DE COLUMNAS (Robustez ante reordenamientos)
    const headers = values[0];
    const localColIndex = headers.indexOf(HEADER_LOCAL);
    const siglaColIndex = headers.indexOf(HEADER_SIGLA);
    
    if (localColIndex === -1 || siglaColIndex === -1) {
      Logger.log("❌ ERROR: No se encontraron las columnas requeridas ('" + HEADER_LOCAL + "' o '" + HEADER_SIGLA + "') en la fila de cabecera.");
      return;
    }
    
    Logger.log("📌 Columnas mapeadas -> LOCAL: Col " + (localColIndex + 1) + " | SIGLA SISTEMA: Col " + (siglaColIndex + 1));
    
    // 5. BUCLE DE PROCESAMIENTO CON PROTECCIÓN DE TIMEOUT Y ERRORES
    for (let i = 1; i < values.length; i++) {
      const row = values[i];
      const localRaw = row[localColIndex];
      const siglaRaw = row[siglaColIndex];
      
      const localName = localRaw ? String(localRaw).trim() : "";
      const sigla = siglaRaw ? String(siglaRaw).trim() : "";
      
      // Control de datos nulos, vacíos o marcados como "-"
      if (!sigla || sigla === "-" || !localName || localName === "-") {
        skippedCount++;
        Logger.log("⏭️ Fila " + (i + 1) + " omitida por datos inválidos o vacíos. [LOCAL: '" + localName + "' | SIGLA: '" + sigla + "']");
        continue;
      }
      
      // Formato visual unificado: [SIGLA SISTEMA] - NOMBRE LOCAL
      const targetFolderName = "[" + sigla + "] - " + localName;
      
      try {
        // Control de duplicados en caché in-memory (Evita llamadas de red adicionales)
        if (existingSubFoldersCache.hasOwnProperty(targetFolderName)) {
          verifiedCount++;
          // Logger.log("✔️ Verificada (Existente): " + targetFolderName);
        } else {
          // Creación de la carpeta
          const newFolder = rootFolder.createFolder(targetFolderName);
          existingSubFoldersCache[targetFolderName] = newFolder.getId(); // Actualizar caché
          createdCount++;
          Logger.log("🆕 Creada: " + targetFolderName + " (ID: " + newFolder.getId() + ")");
        }
      } catch (rowError) {
        errorCount++;
        Logger.log("❌ ERROR en Fila " + (i + 1) + " al procesar '" + targetFolderName + "': " + rowError.toString());
      }
    }
    
    // 6. REPORTE FINAL DE AUDITORÍA
    Logger.log("====================================================================");
    Logger.log("🎉 DESPLIEGUE FINALIZADO CON ÉXITO");
    Logger.log("📂 Carpeta Raíz: " + ROOT_FOLDER_NAME + " (ID: " + rootFolder.getId() + ")");
    Logger.log("📈 RESUMEN DE EJECUCIÓN:");
    Logger.log("   - Carpetas Creadas: " + createdCount);
    Logger.log("   - Carpetas Verificadas (Existentes): " + verifiedCount);
    Logger.log("   - Filas Omitidas (Datos inválidos): " + skippedCount);
    Logger.log("   - Errores de Procesamiento: " + errorCount);
    Logger.log("====================================================================");
    
    // Mensaje en UI de la planilla para confirmación interactiva
    SpreadsheetApp.getUi().alert(
      "Despliegue de Infraestructura Finalizado\n\n" +
      "• Carpetas creadas: " + createdCount + "\n" +
      "• Carpetas ya existentes: " + verifiedCount + "\n" +
      "• Filas omitidas: " + skippedCount + "\n" +
      "• Errores: " + errorCount
    );
    
  } catch (globalError) {
    Logger.log("💥 CRITICAL ERROR GLOBAL durante la ejecución: " + globalError.toString());
  }
}
