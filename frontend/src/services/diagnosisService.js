import { mockResponses, defaultDiagnoses } from '../data/mockData';

export async function getDiagnoses(userMessage) {
  // Имитация задержки сети
  await new Promise((resolve) => setTimeout(resolve, 1200));

  const lowerMsg = userMessage.toLowerCase();

  for (const entry of mockResponses) {
    const matched = entry.keywords.some((kw) => lowerMsg.includes(kw));
    if (matched) {
      return entry.diagnoses;
    }
  }

  return defaultDiagnoses;
}
