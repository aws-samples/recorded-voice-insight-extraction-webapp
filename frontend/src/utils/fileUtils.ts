// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Check if a file has a valid extension for media upload
 * @param filename The name of the file to validate
 * @returns true if the file extension is valid, false otherwise
 */
export const checkValidFileExtension = (filename: string): boolean => {
  const validExtensions = new Set(['mp3', 'mp4', 'wav', 'flac', 'ogg', 'amr', 'webm', 'm4a']);
  const extension = filename.split('.').pop()?.toLowerCase();
  return extension ? validExtensions.has(extension) : false;
};

/**
 * URL encode a filename using encodeURIComponent (similar to Python's urllib.parse.quote_plus)
 * @param filename The filename to encode
 * @returns The URL-encoded filename
 */
export const urlEncodeFilename = (filename: string): string => {
  return encodeURIComponent(filename);
};

/**
 * URL decode a filename using decodeURIComponent
 * @param filename The URL-encoded filename to decode
 * @returns The decoded filename
 */
export const urlDecodeFilename = (filename: string): string => {
  try {
    return decodeURIComponent(filename);
  } catch (error) {
    // If decoding fails, return original filename
    return filename;
  }
};

/**
 * Get the list of valid file extensions as a string for display
 * @returns Comma-separated string of valid extensions
 */
export const getValidExtensionsString = (): string => {
  return 'mp3, mp4, wav, flac, ogg, amr, webm, m4a';
};
