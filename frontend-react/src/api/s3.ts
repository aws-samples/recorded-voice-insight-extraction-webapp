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
  const response = await fetch('/api/s3-presigned', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authToken
    },
    body: JSON.stringify({
      operation: 'GET',
      media_name: mediaName,
      username: username,
      media_type: 'recordings'  // This is the S3 prefix for media files
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to get presigned URL: ${response.statusText}`);
  }

  const data = await response.json();
  return data.url;
}
