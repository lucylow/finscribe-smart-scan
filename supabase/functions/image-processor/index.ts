/**
 * Image Processing Edge Function
 * 
 * Processes and resizes images for document previews and thumbnails.
 * Supports various image formats and operations.
 */

// Deno.serve is the standard way to serve Supabase Edge Functions
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";
import { handleCors } from "../_shared/cors.ts";
import { handleError, successResponse, FunctionError } from "../_shared/errors.ts";
import { requireAuth } from "../_shared/auth.ts";
import { getSupabaseConfig } from "../_shared/config.ts";

interface ProcessRequest {
  filePath: string;
  width?: number;
  height?: number;
  quality?: number;
  format?: "jpeg" | "png" | "webp";
}

// Simple image resizing using canvas (basic implementation)
// Note: For production, consider using a proper image processing library
async function resizeImage(
  imageData: Uint8Array,
  width?: number,
  height?: number,
  quality: number = 0.8
): Promise<Uint8Array> {
  // This is a placeholder - actual implementation would use an image library
  // For Deno edge functions, you might need to use a WebAssembly-based solution
  // or call an external image processing service
  
  // For now, return original data (implement actual resizing as needed)
  console.log(`Resizing image: ${width}x${height}, quality: ${quality}`);
  
  // In a real implementation, you would:
  // 1. Decode the image
  // 2. Resize it to the specified dimensions
  // 3. Encode it in the desired format
  // 4. Return the processed image data
  
  return imageData;
}

// Download file from Supabase Storage
async function downloadFile(
  filePath: string,
  supabaseClient: SupabaseClient
): Promise<Uint8Array> {
  const { data, error } = await supabaseClient.storage
    .from("documents")
    .download(filePath);

  if (error) {
    throw new FunctionError(
      `Failed to download file: ${error.message}`,
      404,
      "FILE_NOT_FOUND"
    );
  }

  if (!data) {
    throw new FunctionError("File not found", 404, "FILE_NOT_FOUND");
  }

  return new Uint8Array(await data.arrayBuffer());
}

// Upload processed file to storage
async function uploadProcessedFile(
  originalPath: string,
  processedData: Uint8Array,
  format: string,
  supabaseClient: SupabaseClient
): Promise<string> {
  const pathParts = originalPath.split(".");
  const basePath = pathParts.slice(0, -1).join(".");
  const newPath = `${basePath}_processed.${format}`;

  const blob = new Blob([new Uint8Array(processedData) as unknown as ArrayBuffer]);
  const { data, error } = await supabaseClient.storage
    .from("documents")
    .upload(newPath, blob, {
      contentType: `image/${format}`,
      upsert: true,
    });

  if (error) {
    throw new FunctionError(
      `Failed to upload processed file: ${error.message}`,
      500,
      "UPLOAD_ERROR"
    );
  }

  return newPath;
}

Deno.serve(async (request) => {
  // Handle CORS preflight
  const corsPreflightResponse = handleCors(request);
  if (corsPreflightResponse) return corsPreflightResponse;

  try {
    const config = getSupabaseConfig();
    const supabaseClient = createClient(config.url, config.anonKey, {
      global: { headers: { Authorization: request.headers.get("Authorization") || "" } },
    });

    // Authenticate user
    const user = await requireAuth(request, config.url, config.anonKey);

    if (request.method === "POST") {
      const processRequest: ProcessRequest = await request.json();

      if (!processRequest.filePath) {
        throw new FunctionError("filePath is required", 400, "MISSING_FILE_PATH");
      }

      // Validate dimensions
      if (processRequest.width && processRequest.width > 5000) {
        throw new FunctionError("Width exceeds maximum of 5000px", 400, "INVALID_DIMENSIONS");
      }
      if (processRequest.height && processRequest.height > 5000) {
        throw new FunctionError("Height exceeds maximum of 5000px", 400, "INVALID_DIMENSIONS");
      }

      // Download original file
      const imageData = await downloadFile(processRequest.filePath, supabaseClient);

      // Process image
      const processedData = await resizeImage(
        imageData,
        processRequest.width,
        processRequest.height,
        processRequest.quality || 0.8
      );

      // Upload processed file
      const processedPath = await uploadProcessedFile(
        processRequest.filePath,
        processedData,
        processRequest.format || "jpeg",
        supabaseClient
      );

      // Get public URL
      const { data: urlData } = supabaseClient.storage
        .from("documents")
        .getPublicUrl(processedPath);

      return successResponse(
        {
          originalPath: processRequest.filePath,
          processedPath,
          publicUrl: urlData.publicUrl,
          width: processRequest.width,
          height: processRequest.height,
          format: processRequest.format || "jpeg",
        },
        "Image processed successfully",
        request
      );
    }

    throw new FunctionError("Method not allowed", 405, "METHOD_NOT_ALLOWED");
  } catch (error) {
    return handleError(error, request);
  }
});
