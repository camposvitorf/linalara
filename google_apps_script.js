/**
 * ==============================================================================
 * GOOGLE APPS SCRIPT: API Webhook para o Enxoval Lina & Lara (Streamlit)
 * ==============================================================================
 * 
 * INSTRUÇÕES:
 * 1. Abra sua planilha: https://docs.google.com/spreadsheets/d/1J2O0GmpNjt91Dhl70HQtobWlh0KrAOXjHLekxX6_Njw/edit
 * 2. No menu superior, clique em "Extensões" (Extensions) > "Apps Script".
 * 3. Apague todo o conteúdo que estiver no editor e cole todo este código.
 * 4. Clique no ícone de disquete ("Salvar projeto" / Ctrl+S).
 * 5. Clique no botão azul "Implantar" (Deploy) > "Nova implantação" (New deployment).
 * 6. Na engrenagem ao lado de "Selecione o tipo", escolha "App da Web" (Web app).
 * 7. Configure os campos:
 *    - Descrição: API Enxoval Lina e Lara
 *    - Executar como: "Eu" (seu e-mail do Google)
 *    - Quem tem acesso: "Qualquer pessoa" (Anyone)
 * 8. Clique em "Implantar".
 *    (Se o Google pedir autorização, clique em "Avançado" e depois em "Acessar... (não seguro)").
 * 9. Copie a "URL do App da Web" gerada (termina com "/exec").
 * 10. Cole essa URL no seu Streamlit (nas Secrets do Streamlit Cloud ou no secrets.toml local).
 * ==============================================================================
 */

function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();
    
    // Se a planilha estiver vazia ou tiver apenas o cabeçalho
    if (!data || data.length <= 1) {
      return ContentService
        .createTextOutput(JSON.stringify([]))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var headers = data[0];
    var items = [];
    
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      // Ignora linhas totalmente vazias
      if (!row[0] && !row[1]) continue;
      
      var item = {};
      for (var j = 0; j < headers.length; j++) {
        var key = String(headers[j]).trim();
        item[key] = row[j];
      }
      
      // Converte tipos numéricos para consistência com o Python
      item.likes = Number(item.likes) || 0;
      item.dislikes = Number(item.dislikes) || 0;
      item.tenho = Number(item.tenho) || 0;
      item.qtd_necessaria = Number(item.qtd_necessaria) || 1;
      item.title = String(item.title || "").trim();
      item.link = String(item.link || "").trim();
      item.image_url = String(item.image_url || "").trim();
      
      items.push(item);
    }
    
    return ContentService
      .createTextOutput(JSON.stringify(items))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var contents = e.postData.contents;
    var items = JSON.parse(contents);
    
    // Limpa a planilha atual para regravar os dados atualizados
    sheet.clearContents();
    
    var headers = ["title", "link", "image_url", "likes", "dislikes", "tenho", "qtd_necessaria"];
    var outputRows = [headers];
    
    if (Array.isArray(items) && items.length > 0) {
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        outputRows.push([
          String(it.title || ""),
          String(it.link || ""),
          String(it.image_url || ""),
          Number(it.likes) || 0,
          Number(it.dislikes) || 0,
          Number(it.tenho) || 0,
          Number(it.qtd_necessaria) || 1
        ]);
      }
    }
    
    sheet.getRange(1, 1, outputRows.length, headers.length).setValues(outputRows);
    
    // Formatação visual básica no cabeçalho
    sheet.getRange(1, 1, 1, headers.length)
      .setFontWeight("bold")
      .setBackground("#ffeaf1")
      .setFontColor("#d85a8a");
      
    return ContentService
      .createTextOutput(JSON.stringify({ status: "success", count: items.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
