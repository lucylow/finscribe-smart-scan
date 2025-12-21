import { BoundingBox } from '@/components/finscribe/ImageViewer';

/**
 * Extract bounding boxes from OCR results
 * Supports multiple OCR output formats:
 * - PaddleOCR-VL format: { tokens: [], bboxes: [] }
 * - Regions format: { regions: [] }
 * - Field extraction format: { extracted_fields: [] }
 */
export function extractBoundingBoxes(
  ocrResults: Record<string, unknown>,
  imageWidth?: number,
  imageHeight?: number
): BoundingBox[] {
  const boxes: BoundingBox[] = [];

  // Format 1: PaddleOCR-VL format with tokens and bboxes
  if ('tokens' in ocrResults && 'bboxes' in ocrResults) {
    const tokens = ocrResults.tokens as Array<Record<string, unknown> | string>;
    const bboxes = ocrResults.bboxes as Array<Record<string, unknown> | number[]>;

    tokens.forEach((token, index) => {
      const bboxData = bboxes[index];
      if (!bboxData) return;

      let x1 = 0,
        y1 = 0,
        x2 = 0,
        y2 = 0;

      // Handle different bbox formats
      if (Array.isArray(bboxData)) {
        // Format: [x1, y1, x2, y2] or [x, y, w, h]
        if (bboxData.length >= 4) {
          if (bboxData.length === 4) {
            // Could be [x, y, w, h] or [x1, y1, x2, y2]
            // Assume [x, y, w, h] if w and h are reasonable
            const [a, b, c, d] = bboxData;
            if (c > 0 && c < 10000 && d > 0 && d < 10000) {
              // Likely [x, y, w, h]
              x1 = Number(a);
              y1 = Number(b);
              x2 = x1 + Number(c);
              y2 = y1 + Number(d);
            } else {
              // Likely [x1, y1, x2, y2]
              x1 = Number(a);
              y1 = Number(b);
              x2 = Number(c);
              y2 = Number(d);
            }
          } else if (bboxData.length >= 8) {
            // Polygon format: [x1, y1, x2, y2, x3, y3, x4, y4]
            const xs = [bboxData[0], bboxData[2], bboxData[4], bboxData[6]].map(Number);
            const ys = [bboxData[1], bboxData[3], bboxData[5], bboxData[7]].map(Number);
            x1 = Math.min(...xs);
            y1 = Math.min(...ys);
            x2 = Math.max(...xs);
            y2 = Math.max(...ys);
          }
        }
      } else if (typeof bboxData === 'object' && bboxData !== null) {
        // Format: { x, y, w, h } or { x1, y1, x2, y2 }
        const bbox = bboxData as Record<string, unknown>;
        if ('x' in bbox && 'y' in bbox && 'w' in bbox && 'h' in bbox) {
          x1 = Number(bbox.x) || 0;
          y1 = Number(bbox.y) || 0;
          const w = Number(bbox.w) || 0;
          const h = Number(bbox.h) || 0;
          x2 = x1 + w;
          y2 = y1 + h;
        } else if ('x1' in bbox && 'y1' in bbox && 'x2' in bbox && 'y2' in bbox) {
          x1 = Number(bbox.x1) || 0;
          y1 = Number(bbox.y1) || 0;
          x2 = Number(bbox.x2) || 0;
          y2 = Number(bbox.y2) || 0;
        }
      }

      // Normalize coordinates if image dimensions are provided
      let normalizedX = x1;
      let normalizedY = y1;
      let normalizedWidth = x2 - x1;
      let normalizedHeight = y2 - y1;

      if (imageWidth && imageHeight && imageWidth > 0 && imageHeight > 0) {
        normalizedX = x1 / imageWidth;
        normalizedY = y1 / imageHeight;
        normalizedWidth = (x2 - x1) / imageWidth;
        normalizedHeight = (y2 - y1) / imageHeight;
      } else if (x2 > 1 || y2 > 1) {
        // Assume coordinates are in pixels, but we don't have image dimensions
        // This is a fallback - ideally we'd have image dimensions
        console.warn('Bounding box coordinates appear to be in pixels but image dimensions not provided');
      }

      const tokenText = typeof token === 'string' ? token : (token?.text as string) || '';
      const confidence = typeof token === 'object' && token !== null
        ? (token.confidence as number) || 0.9
        : 0.9;
      const regionType = typeof bboxData === 'object' && bboxData !== null
        ? (bboxData.region_type as string) || 'other'
        : 'other';

      // Map region type to field type
      let fieldType: BoundingBox['fieldType'] = 'other';
      if (regionType.includes('vendor') || regionType.includes('company')) {
        fieldType = 'vendor';
      } else if (regionType.includes('invoice') || regionType.includes('date') || regionType.includes('number')) {
        fieldType = 'invoice_info';
      } else if (regionType.includes('line') || regionType.includes('item')) {
        fieldType = 'line_item';
      } else if (regionType.includes('total') || regionType.includes('sum')) {
        fieldType = 'totals';
      }

      boxes.push({
        id: `bbox-${index}`,
        x: Math.max(0, Math.min(1, normalizedX)),
        y: Math.max(0, Math.min(1, normalizedY)),
        width: Math.max(0, Math.min(1, normalizedWidth)),
        height: Math.max(0, Math.min(1, normalizedHeight)),
        label: tokenText || `Region ${index + 1}`,
        confidence,
        fieldType,
        fieldId: `field-${index}`,
      });
    });
  }

  // Format 2: Regions format
  else if ('regions' in ocrResults) {
    const regions = ocrResults.regions as Array<Record<string, unknown>>;
    regions.forEach((region, index) => {
      const bbox = region.bbox as Record<string, unknown> | number[] | undefined;
      if (!bbox) return;

      let x1 = 0,
        y1 = 0,
        x2 = 0,
        y2 = 0;

      if (Array.isArray(bbox)) {
        if (bbox.length >= 4) {
          x1 = Number(bbox[0]) || 0;
          y1 = Number(bbox[1]) || 0;
          x2 = Number(bbox[2]) || 0;
          y2 = Number(bbox[3]) || 0;
        }
      } else if (typeof bbox === 'object' && bbox !== null) {
        const b = bbox as Record<string, unknown>;
        if ('x' in b && 'y' in b && 'w' in b && 'h' in b) {
          x1 = Number(b.x) || 0;
          y1 = Number(b.y) || 0;
          x2 = x1 + (Number(b.w) || 0);
          y2 = y1 + (Number(b.h) || 0);
        } else if ('x1' in b && 'y1' in b && 'x2' in b && 'y2' in b) {
          x1 = Number(b.x1) || 0;
          y1 = Number(b.y1) || 0;
          x2 = Number(b.x2) || 0;
          y2 = Number(b.y2) || 0;
        }
      }

      // Normalize coordinates
      let normalizedX = x1;
      let normalizedY = y1;
      let normalizedWidth = x2 - x1;
      let normalizedHeight = y2 - y1;

      if (imageWidth && imageHeight && imageWidth > 0 && imageHeight > 0) {
        normalizedX = x1 / imageWidth;
        normalizedY = y1 / imageHeight;
        normalizedWidth = (x2 - x1) / imageWidth;
        normalizedHeight = (y2 - y1) / imageHeight;
      }

      const regionType = (region.type as string) || 'other';
      let fieldType: BoundingBox['fieldType'] = 'other';
      if (regionType.includes('vendor') || regionType.includes('company')) {
        fieldType = 'vendor';
      } else if (regionType.includes('invoice') || regionType.includes('date') || regionType.includes('number')) {
        fieldType = 'invoice_info';
      } else if (regionType.includes('line') || regionType.includes('item')) {
        fieldType = 'line_item';
      } else if (regionType.includes('total') || regionType.includes('sum')) {
        fieldType = 'totals';
      }

      boxes.push({
        id: `region-${index}`,
        x: Math.max(0, Math.min(1, normalizedX)),
        y: Math.max(0, Math.min(1, normalizedY)),
        width: Math.max(0, Math.min(1, normalizedWidth)),
        height: Math.max(0, Math.min(1, normalizedHeight)),
        label: (region.content as string) || (region.label as string) || `Region ${index + 1}`,
        confidence: (region.confidence as number) || 0.9,
        fieldType,
        fieldId: `field-${index}`,
      });
    });
  }

  // Format 3: Field extraction format
  else if ('extracted_fields' in ocrResults) {
    const fields = ocrResults.extracted_fields as Array<Record<string, unknown>>;
    fields.forEach((field, index) => {
      const bbox = field.bbox as number[] | undefined;
      if (!bbox || !Array.isArray(bbox) || bbox.length < 4) return;

      const [x1, y1, x2, y2] = bbox.map(Number);

      // Normalize coordinates
      let normalizedX = x1;
      let normalizedY = y1;
      let normalizedWidth = x2 - x1;
      let normalizedHeight = y2 - y1;

      if (imageWidth && imageHeight && imageWidth > 0 && imageHeight > 0) {
        normalizedX = x1 / imageWidth;
        normalizedY = y1 / imageHeight;
        normalizedWidth = (x2 - x1) / imageWidth;
        normalizedHeight = (y2 - y1) / imageHeight;
      }

      const fieldName = (field.field_name as string) || '';
      let fieldType: BoundingBox['fieldType'] = 'other';
      if (fieldName.includes('vendor') || fieldName.includes('company')) {
        fieldType = 'vendor';
      } else if (fieldName.includes('invoice') || fieldName.includes('date') || fieldName.includes('number')) {
        fieldType = 'invoice_info';
      } else if (fieldName.includes('line') || fieldName.includes('item')) {
        fieldType = 'line_item';
      } else if (fieldName.includes('total') || fieldName.includes('sum')) {
        fieldType = 'totals';
      }

      boxes.push({
        id: `field-${index}`,
        x: Math.max(0, Math.min(1, normalizedX)),
        y: Math.max(0, Math.min(1, normalizedY)),
        width: Math.max(0, Math.min(1, normalizedWidth)),
        height: Math.max(0, Math.min(1, normalizedHeight)),
        label: fieldName || `Field ${index + 1}`,
        confidence: (field.confidence as number) || 0.9,
        fieldType,
        fieldId: fieldName,
      });
    });
  }

  return boxes;
}

/**
 * Convert extracted data to corrections format
 */
export function dataToCorrections(
  data: Record<string, unknown>
): import('@/components/finscribe/CorrectionsPanel').CorrectionsData {
  const corrections: import('@/components/finscribe/CorrectionsPanel').CorrectionsData = {};

  // Vendor information
  if (data.vendor || data.vendor_block) {
    const vendor = (data.vendor || data.vendor_block) as Record<string, unknown>;
    corrections.vendor = {
      name: {
        value: vendor.name || vendor.company_name || null,
        isValid: true,
        isDirty: false,
      },
      address: {
        value: vendor.address || null,
        isValid: true,
        isDirty: false,
      },
      taxId: {
        value: vendor.tax_id || vendor.taxId || null,
        isValid: true,
        isDirty: false,
      },
      contact: {
        value: vendor.contact || vendor.email || vendor.phone || null,
        isValid: true,
        isDirty: false,
      },
    };
  }

  // Invoice information
  if (data.invoice_info || data.invoice_number || data.date) {
    corrections.invoice_info = {
      invoiceNumber: {
        value: data.invoice_number || data.invoice_info?.invoice_number || null,
        isValid: true,
        isDirty: false,
      },
      date: {
        value: data.date || data.invoice_info?.date || null,
        isValid: true,
        isDirty: false,
      },
      poNumber: {
        value: data.po_number || data.invoice_info?.po_number || null,
        isValid: true,
        isDirty: false,
      },
      dueDate: {
        value: data.due_date || data.invoice_info?.due_date || null,
        isValid: true,
        isDirty: false,
      },
    };
  }

  // Line items
  if (data.line_items && Array.isArray(data.line_items)) {
    corrections.line_items = data.line_items.map((item: Record<string, unknown>) => ({
      description: {
        value: item.description || null,
        isValid: true,
        isDirty: false,
      },
      quantity: {
        value: item.quantity || null,
        isValid: true,
        isDirty: false,
      },
      unitPrice: {
        value: item.unit_price || item.unitPrice || null,
        isValid: true,
        isDirty: false,
      },
      lineTotal: {
        value: item.line_total || item.lineTotal || null,
        isValid: true,
        isDirty: false,
      },
    }));
  }

  // Totals
  if (data.total || data.totals || data.financial_summary) {
    const totals = (data.totals || data.financial_summary || {}) as Record<string, unknown>;
    corrections.totals = {
      subtotal: {
        value: totals.subtotal || data.subtotal || null,
        isValid: true,
        isDirty: false,
      },
      tax: {
        value: totals.tax || data.tax || null,
        isValid: true,
        isDirty: false,
      },
      discount: {
        value: totals.discount || data.discount || null,
        isValid: true,
        isDirty: false,
      },
      total: {
        value: data.total || totals.total || null,
        isValid: true,
        isDirty: false,
      },
    };
  }

  return corrections;
}

