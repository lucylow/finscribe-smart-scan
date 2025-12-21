import { supabase } from './client';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { Database } from './types';

/**
 * Utility functions for common Supabase operations
 */

/**
 * Handle Supabase errors with better error messages
 */
export function handleSupabaseError(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    const supabaseError = error as { message: string; code?: string };
    return supabaseError.message || 'An unexpected error occurred';
  }
  return 'An unexpected error occurred';
}

/**
 * Check if an error is a Supabase error
 */
export function isSupabaseError(error: unknown): boolean {
  return error !== null && typeof error === 'object' && 'message' in error;
}

/**
 * Get a typed Supabase client instance
 */
export function getClient(): SupabaseClient<Database> {
  return supabase;
}

/**
 * Upload a file to Supabase Storage
 */
export async function uploadFile(
  bucket: string,
  path: string,
  file: File | Blob,
  options?: {
    cacheControl?: string;
    contentType?: string;
    upsert?: boolean;
  }
) {
  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(path, file, {
      cacheControl: options?.cacheControl || '3600',
      contentType: options?.contentType || file.type,
      upsert: options?.upsert || false,
    });

  if (error) throw error;
  return data;
}

/**
 * Get a public URL for a file in Supabase Storage
 */
export function getPublicUrl(bucket: string, path: string): string {
  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  return data.publicUrl;
}

/**
 * Delete a file from Supabase Storage
 */
export async function deleteFile(bucket: string, paths: string[]) {
  const { data, error } = await supabase.storage.from(bucket).remove(paths);
  if (error) throw error;
  return data;
}

/**
 * List files in a Supabase Storage bucket
 */
export async function listFiles(
  bucket: string,
  path?: string,
  options?: {
    limit?: number;
    offset?: number;
    sortBy?: { column: string; order?: 'asc' | 'desc' };
  }
) {
  let query = supabase.storage.from(bucket).list(path || '', {
    limit: options?.limit || 100,
    offset: options?.offset || 0,
    sortBy: options?.sortBy || { column: 'name', order: 'asc' },
  });

  const { data, error } = await query;
  if (error) throw error;
  return data;
}

/**
 * Download a file from Supabase Storage
 */
export async function downloadFile(bucket: string, path: string) {
  const { data, error } = await supabase.storage.from(bucket).download(path);
  if (error) throw error;
  return data;
}

/**
 * Realtime subscription helper
 */
export function subscribeToTable<T>(
  table: string,
  filter?: string,
  callback: (payload: { eventType: 'INSERT' | 'UPDATE' | 'DELETE'; new?: T; old?: T }) => void
) {
  const channel = supabase
    .channel(`${table}-changes`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table,
        filter: filter,
      },
      (payload) => {
        callback({
          eventType: payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE',
          new: payload.new as T,
          old: payload.old as T,
        });
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}

/**
 * Batch insert helper with error handling
 */
export async function batchInsert<T>(
  table: string,
  rows: unknown[],
  options?: { returning?: 'minimal' | 'representation' }
) {
  const { data, error } = await supabase
    .from(table)
    .insert(rows)
    .select(options?.returning === 'minimal' ? undefined : '*');

  if (error) throw error;
  return data as T[];
}

/**
 * Batch update helper
 */
export async function batchUpdate<T>(
  table: string,
  updates: Record<string, unknown>,
  filter: string,
  filterValue: unknown
) {
  const { data, error } = await supabase
    .from(table)
    .update(updates)
    .eq(filter, filterValue)
    .select();

  if (error) throw error;
  return data as T[];
}

/**
 * Batch delete helper
 */
export async function batchDelete(table: string, filter: string, filterValue: unknown) {
  const { data, error } = await supabase.from(table).delete().eq(filter, filterValue).select();
  if (error) throw error;
  return data;
}

/**
 * Pagination helper for Supabase queries
 */
export interface PaginationOptions {
  page?: number;
  pageSize?: number;
  orderBy?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResult<T> {
  data: T[];
  page: number;
  pageSize: number;
  total: number;
  hasMore: boolean;
}

export async function paginateQuery<T>(
  query: ReturnType<typeof supabase.from>,
  options: PaginationOptions = {}
): Promise<PaginatedResult<T>> {
  const page = options.page || 1;
  const pageSize = options.pageSize || 20;
  const from = (page - 1) * pageSize;
  const to = from + pageSize - 1;

  let q = query.select('*', { count: 'exact' }).range(from, to);

  if (options.orderBy) {
    q = q.order(options.orderBy, { ascending: options.order === 'asc' });
  }

  const { data, error, count } = await q;
  if (error) throw error;

  return {
    data: (data || []) as T[],
    page,
    pageSize,
    total: count || 0,
    hasMore: (count || 0) > to + 1,
  };
}

