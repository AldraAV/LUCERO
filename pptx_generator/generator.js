import fs from 'fs';
import path from 'path';
import pptxgen from 'pptxgenjs';

// Validar argumentos
if (process.argv.length < 4) {
  console.error(JSON.stringify({
    success: false,
    error: "Uso requerido: node generator.js <ruta_json_entrada> <ruta_pptx_salida>"
  }));
  process.exit(1);
}

const inputJsonPath = process.argv[2];
const outputPptxPath = process.argv[3];

try {
  // Leer y parsear JSON
  const rawData = fs.readFileSync(inputJsonPath, 'utf8');
  const presentationData = JSON.parse(rawData);

  // Inicializar pptxgen
  const pres = new pptxgen();
  
  // Establecer título del documento
  if (presentationData.title) {
    pres.title = presentationData.title;
  }
  
  // Procesar slides
  const slidesData = presentationData.slides || [];
  
  for (const slideSpec of slidesData) {
    const slide = pres.addSlide();
    
    // Color de fondo de la diapositiva
    if (slideSpec.backgroundColor) {
      slide.background = { fill: slideSpec.backgroundColor };
    } else if (presentationData.theme?.backgroundColor) {
      slide.background = { fill: presentationData.theme.backgroundColor };
    }
    
    // Título de la diapositiva (elemento nativo simplificado)
    if (slideSpec.title) {
      slide.addText(slideSpec.title, {
        x: 0.5,
        y: 0.4,
        w: 9.0,
        h: 0.8,
        fontSize: slideSpec.titleFontSize || 32,
        bold: true,
        color: slideSpec.titleColor || presentationData.theme?.accentColor || '000000',
        fontFace: 'Space Grotesk'
      });
    }
    
    // Elementos dentro del slide
    const elements = slideSpec.elements || [];
    for (const elem of elements) {
      const type = elem.type;
      const opts = elem.options || {};
      
      // Mapear opciones comunes de formato
      const formattedOpts = {
        x: opts.x ?? 1.0,
        y: opts.y ?? 1.5,
        w: opts.w ?? 8.0,
        h: opts.h ?? 1.0,
        fontSize: opts.fontSize ?? 14,
        bold: opts.bold ?? false,
        italic: opts.italic ?? false,
        underline: opts.underline ?? false,
        color: opts.color ?? presentationData.theme?.textColor ?? '333333',
        align: opts.align ?? 'left',
        fontFace: opts.fontFace ?? 'Inter'
      };
      
      if (type === 'text') {
        slide.addText(elem.value || '', formattedOpts);
      } 
      else if (type === 'image') {
        const imgPath = elem.value;
        if (imgPath && fs.existsSync(imgPath)) {
          slide.addImage({
            path: imgPath,
            x: formattedOpts.x,
            y: formattedOpts.y,
            w: formattedOpts.w,
            h: formattedOpts.h
          });
        } else {
          console.error(`Advertencia: La imagen no existe o no se especificó: ${imgPath}`);
        }
      } 
      else if (type === 'table') {
        const rows = elem.value || []; // matriz [[cell1, cell2], ...] o [{text, options}]
        // Mapeo opcional de estilos de celda para estructurar la tabla
        slide.addTable(rows, {
          x: formattedOpts.x,
          y: formattedOpts.y,
          w: formattedOpts.w,
          h: formattedOpts.h,
          fontSize: opts.fontSize ?? 12,
          fontFace: opts.fontFace ?? 'Inter',
          color: opts.color ?? '000000',
          border: opts.border ?? { type: 'solid', color: 'CCCCCC', pt: 1 },
          fill: opts.fill ?? 'FFFFFF',
          headerRow: opts.headerRow ?? false
        });
      }
    }
  }

  // Guardar archivo
  pres.writeFile({ fileName: outputPptxPath })
    .then(fileName => {
      console.log(JSON.stringify({
        success: true,
        output: outputPptxPath,
        slides_count: slidesData.length
      }));
      process.exit(0);
    })
    .catch(err => {
      console.error(JSON.stringify({
        success: false,
        error: `Fallo al escribir el archivo PPTX: ${err.message}`
      }));
      process.exit(1);
    });

} catch (err) {
  console.error(JSON.stringify({
    success: false,
    error: `Error interno de procesamiento: ${err.message}`
  }));
  process.exit(1);
}
