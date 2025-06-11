/**
 * Functions for interacting with S3 via API Gateway
 */

/**
 * Get a presigned URL for a media file
 * @param mediaName The name of the media file
 * @param username The current user's username
 * @param authToken The authentication token
 * @returns Promise resolving to the presigned URL
 */
export async function getMediaPresignedUrl(
  mediaName: string,
  username: string,
  authToken: string
): Promise<string> {
  console.log(`🔗 Requesting presigned URL for: ${mediaName}`);
  
  const response = await fetch('/api/s3-presigned', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authToken
    },
    body: JSON.stringify({
      action: 'download_media_file',  // Backend expects 'action', not 'operation'
      media_file_name: mediaName,     // Backend expects 'media_file_name', not 'media_name'
      username: username
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error(`❌ Presigned URL request failed: ${response.status} ${response.statusText}`, errorText);
    throw new Error(`Failed to get presigned URL: ${response.statusText}`);
  }

  const data = await response.json();
  console.log(`✅ Received presigned URL response:`, data);
  
  // The backend returns the presigned URL directly as a string, not in a 'url' field
  return typeof data === 'string' ? data : data.url || data;
}
