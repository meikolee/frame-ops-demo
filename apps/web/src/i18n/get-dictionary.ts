import type { Dictionary } from "./dictionaries/en";
import { en } from "./dictionaries/en";
import { zh } from "./dictionaries/zh";
import type { Locale } from "./config";

export type { Dictionary };

const dictionaries: Record<Locale, Dictionary> = {
  zh,
  en,
};

export async function getDictionary(locale: Locale): Promise<Dictionary> {
  return dictionaries[locale];
}
