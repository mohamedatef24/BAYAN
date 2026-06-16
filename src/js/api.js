// src/js/api.js
export async function analyzeText(text) {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  if (!response.ok) throw new Error('Analyze API error');
  return await response.json();
}

export async function summarizeText(text, length = 2, full = true) {
  const response = await fetch('/api/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, length, full_text: full })
  });
  if (!response.ok) throw new Error('Summarize API error');
  return await response.json();
}

export async function getSpelling(text) {
  const response = await fetch('/api/spelling', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  if (!response.ok) throw new Error('Spelling API error');
  return await response.json();
}

export async function getGrammar(text) {
  const response = await fetch('/api/grammar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  if (!response.ok) throw new Error('Grammar API error');
  return await response.json();
}

export async function getPunctuation(text) {
  const response = await fetch('/api/punctuation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  if (!response.ok) throw new Error('Punctuation API error');
  return await response.json();
}
