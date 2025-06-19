// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

export const SUPPORTED_LANGUAGES = [
  'Bulgarian',
  'Croatian',
  'Czech',
  'Danish',
  'Dutch',
  'English',
  'Estonian',
  'Finnish',
  'French',
  'German',
  'Greek',
  'Hungarian',
  'Irish',
  'Italian',
  'Latvian',
  'Lithuanian',
  'Maltese',
  'Polish',
  'Portuguese',
  'Romanian',
  'Slovak',
  'Slovenian',
  'Spanish',
  'Swedish',
] as const;

export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];
