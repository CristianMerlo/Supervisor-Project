/**
 * GOOGLE APPS SCRIPT: WEB APP UPLOADER FOR MOSTAZA REPORTES
 * Recibe el PDF en Base64, busca la carpeta del local y lo guarda usando tu espacio.
 */

function doPost(e) {
  try {
    // 1. Parse the incoming JSON request
    const data = JSON.parse(e.postData.contents);
    const sigla = data.sigla;
    const fileName = data.fileName;
    const fileBase64 = data.fileBase64;
    
    if (!sigla || !fileName || !fileBase64) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Faltan parámetros requeridos: sigla, fileName, o fileBase64."
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 2. Search for the root folder "Mostaza Locales"
    const folderIterator = DriveApp.getFoldersByName("Mostaza Locales");
    let rootFolder = null;
    if (folderIterator.hasNext()) {
      rootFolder = folderIterator.next();
    }
    
    // 3. Search for the store folder containing the sigla
    let targetFolder = null;
    let query = "title contains '" + sigla + "' and trashed = false";
    if (rootFolder) {
      query += " and '" + rootFolder.getId() + "' in parents";
    }
    
    const subFolderIterator = DriveApp.searchFolders(query);
    if (subFolderIterator.hasNext()) {
      targetFolder = subFolderIterator.next();
    }
    
    // Fallback: Search all of Drive for the sigla if not found under "Mostaza Locales"
    if (!targetFolder) {
      const fallbackIterator = DriveApp.searchFolders("title contains '" + sigla + "' and trashed = false");
      if (fallbackIterator.hasNext()) {
        targetFolder = fallbackIterator.next();
      }
    }
    
    if (!targetFolder) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "No se encontró la carpeta del local con la sigla: " + sigla
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 4. Locate or create "Reportes" subfolder inside the store folder
    let destinationFolder = targetFolder;
    const reportesIterator = targetFolder.getFoldersByName("Reportes");
    if (reportesIterator.hasNext()) {
      destinationFolder = reportesIterator.next();
    } else {
      // If "Reportes" subfolder doesn't exist, create it to organize documents cleanly
      try {
        destinationFolder = targetFolder.createFolder("Reportes");
      } catch (err) {
        // Fallback to writing directly in the store folder if subfolder creation fails
        destinationFolder = targetFolder;
      }
    }
    
    // 5. Decode Base64 and write the PDF
    const decodedBytes = Utilities.base64Decode(fileBase64);
    const blob = Utilities.newBlob(decodedBytes, "application/pdf", fileName);
    const newFile = destinationFolder.createFile(blob);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      fileId: newFile.getId()
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
