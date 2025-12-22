/**
 * Document Upload Handler Edge Function
 * 
 * Handles document uploads, validates files, and stores metadata.
 * Supports various document formats (PDF, images, etc.)
 */

// Deno.serve is the standard way to serve Supabase Edge Functions
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { handleCors } from "../_shared/cors.ts";
import { handleError, successResponse, FunctionError } from "../_shared/errors.ts";
import { requireAuth } from "../_shared/auth.ts";
import { getSupabaseConfig } from "../_shared/config.ts";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/tiff",
  "image/webp",
];

interface UploadRequest {
  filename: string;
  file: File;
  metadata?: Record<string, unknown>;
}

// Validate file
function validateFile(file: File): void {
  if (file.size > MAX_FILE_SIZE) {
    throw new FunctionError(
      `File size exceeds maximum of ${MAX_FILE_SIZE / 1024 / 1024}MB`,
      400,
      "FILE_TOO_LARGE"
    );
  }

  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    throw new FunctionError(
      `File type not allowed. Allowed types: ${ALLOWED_MIME_TYPES.join(", ")}`,
      400,
      "INVALID_FILE_TYPE"
    );
  }
}

// Upload file to Supabase Storage
async function uploadToStorage(
  file: File,
  userId: string,
  filename: string,
  // deno-lint-ignore no-explicit-any
  supabaseClient: any
): Promise<string> {
  const fileExt = filename.split(".").pop();
  const filePath = `${userId}/${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`;

  const { data, error } = await supabaseClient.storage
    .from("documents")
    .upload(filePath, file, {
      contentType: file.type,
      upsert: false,
    });

  if (error) {
    throw new FunctionError(
      `Failed to upload file: ${error.message}`,
      500,
      "UPLOAD_ERROR"
    );
  }

  return filePath;
}

// Record document metadata in database
async function recordDocument(
  userId: string,
  filePath: string,
  filename: string,
  fileSize: number,
  mimeType: string,
  metadata: Record<string, unknown> | undefined,
  // deno-lint-ignore no-explicit-any
  supabaseClient: any
): Promise<string> {
  // If you have a documents table, insert here
  // For now, we'll just return the file path
  // You can extend this to insert into a documents table
  
  const documentData = {
    user_id: userId,
    file_path: filePath,
    filename: filename,
    file_size: fileSize,
    mime_type: mimeType,
    metadata: metadata || {},
    created_at: new Date().toISOString(),
    status: "uploaded",
  };

  // Example: Insert into documents table if it exists
  // const { data, error } = await supabaseClient
  //   .from("documents")
  //   .insert(documentData)
  //   .select()
  //   .single();

  // if (error) {
  //   throw new FunctionError(
  //     `Failed to record document: ${error.message}`,
  //     500,
  //     "DATABASE_ERROR"
  //   );
  // }

  // return data.id;

  return filePath;
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

    // Handle file upload
    if (request.method === "POST") {
      const formData = await request.formData();
      const file = formData.get("file") as File | null;
      const metadataJson = formData.get("metadata") as string | null;

      if (!file) {
        throw new FunctionError("No file provided", 400, "MISSING_FILE");
      }

      // Validate file
      validateFile(file);

      // Parse metadata if provided
      let metadata: Record<string, unknown> | undefined;
      if (metadataJson) {
        try {
          metadata = JSON.parse(metadataJson);
        } catch {
          throw new FunctionError("Invalid metadata JSON", 400, "INVALID_METADATA");
        }
      }

      // Upload to storage
      const filePath = await uploadToStorage(file, user.id, file.name, supabaseClient);

      // Record document in database
      const documentId = await recordDocument(
        user.id,
        filePath,
        file.name,
        file.size,
        file.type,
        metadata,
        supabaseClient
      );

      // Get public URL
      const { data: urlData } = supabaseClient.storage
        .from("documents")
        .getPublicUrl(filePath);

      return successResponse(
        {
          documentId,
          filePath,
          publicUrl: urlData.publicUrl,
          filename: file.name,
          size: file.size,
          mimeType: file.type,
        },
        "Document uploaded successfully",
        request
      );
    }

    throw new FunctionError("Method not allowed", 405, "METHOD_NOT_ALLOWED");
  } catch (error) {
    return handleError(error, request);
  }
});

