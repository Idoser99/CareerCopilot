const MAX_FILE_SIZE = 15 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = new Set(["pdf", "docx", "txt"]);

function getExtension(fileName) {
  return String(fileName || "").split(".").pop()?.toLowerCase() || "";
}

async function extractPdfText(file) {
  const [{ getDocument, GlobalWorkerOptions }, workerModule] = await Promise.all([
    import("pdfjs-dist"),
    import("pdfjs-dist/build/pdf.worker.mjs?url"),
  ]);
  GlobalWorkerOptions.workerSrc = workerModule.default;

  const data = await file.arrayBuffer();
  const document = await getDocument({ data }).promise;
  const pages = [];

  try {
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();
      const pageText = content.items
        .map((item) => ("str" in item ? item.str : ""))
        .join(" ")
        .replace(/\s+\n/g, "\n")
        .trim();

      if (pageText) {
        pages.push(pageText);
      }
    }
  } finally {
    await document.destroy();
  }

  return pages.join("\n\n");
}

async function extractDocxText(file) {
  const mammoth = await import("mammoth/mammoth.browser");
  const result = await mammoth.extractRawText({
    arrayBuffer: await file.arrayBuffer(),
  });
  return result.value;
}

export async function extractCvText(file) {
  if (!(file instanceof File)) {
    throw new Error("Choose a CV file to continue.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("The selected file is larger than 15 MB.");
  }

  const extension = getExtension(file.name);
  if (!SUPPORTED_EXTENSIONS.has(extension)) {
    throw new Error("Unsupported file type. Please choose a PDF, DOCX, or TXT file.");
  }

  let text;
  if (extension === "pdf") {
    text = await extractPdfText(file);
  } else if (extension === "docx") {
    text = await extractDocxText(file);
  } else {
    text = await file.text();
  }

  const normalizedText = String(text || "")
    .replaceAll("\r\n", "\n")
    .replaceAll("\r", "\n")
    .replaceAll("\u00a0", " ")
    .trim();

  if (!normalizedText) {
    throw new Error(
      "No readable text was found. Scanned PDFs require OCR and are not supported yet.",
    );
  }

  return normalizedText;
}
