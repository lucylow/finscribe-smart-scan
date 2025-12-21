/**
 * Supabase Integration Exports
 * 
 * This file provides a centralized export point for all Supabase-related functionality.
 */

// Client
export { supabase, isSupabaseConfigured, getSupabaseConfig } from './client';
export type { Database } from './types';

// Utils
export {
  handleSupabaseError,
  isSupabaseError,
  getClient,
  uploadFile,
  getPublicUrl,
  deleteFile,
  listFiles,
  downloadFile,
  subscribeToTable,
  batchInsert,
  batchUpdate,
  batchDelete,
  paginateQuery,
  type PaginationOptions,
  type PaginatedResult,
} from './utils';

// Re-export commonly used types
export type { Json, Tables, TablesInsert, TablesUpdate, Enums, CompositeTypes } from './types';


