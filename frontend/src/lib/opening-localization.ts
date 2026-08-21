const openingFamilies: Record<string, string> = {
  "Sicilian Defense": "Сицилианская защита",
  "Caro-Kann Defense": "Защита Каро-Канн",
  "French Defense": "Французская защита",
  "Queen's Gambit": "Ферзевый гамбит",
  "King's Indian Defense": "Староиндийская защита",
  "English Opening": "Английское начало",
  "Queen's Pawn Game": "Дебют ферзевых пешек",
  "King's Pawn Game": "Дебют королевских пешек",
  "Grob Opening": "Дебют Гроба",
  "Grob Gambit": "Гамбит Гроба",
  "Slav Defense": "Славянская защита",
  "Zukertort Opening": "Дебют Цукерторта",
  "Italian Game": "Итальянская партия",
  "Ruy Lopez": "Испанская партия",
  "Queen's Indian Defense": "Новоиндийская защита",
  "Nimzo-Indian Defense": "Защита Нимцовича",
  "Scandinavian Defense": "Скандинавская защита",
  "Dutch Defense": "Голландская защита",
  "Pirc Defense": "Защита Пирца",
  "Alekhine Defense": "Защита Алехина",
};

const openingVariations: Record<string, string> = {
  "Accepted": "Принятый вариант",
  "Declined": "Отказанный вариант",
  "Exchange Variation": "Разменный вариант",
  "Advance Variation": "Вариант с выдвижением",
  "Classical Variation": "Классический вариант",
  "Modern Variation": "Современный вариант",
  "Najdorf Variation": "Вариант Найдорфа",
  "English Attack": "Английская атака",
  "Spike Attack": "Атака Спайка",
  "Hurst Attack": "Атака Хёрста",
};

export function localizeOpeningFamily(value: string | null | undefined): string | null {
  if (!value) return null;
  return openingFamilies[value] ?? value;
}

export function localizeOpeningVariation(value: string | null | undefined): string | null {
  if (!value) return null;
  return openingVariations[value] ?? value;
}

export function localizeOpeningName(value: string | null | undefined): string | null {
  if (!value) return null;
  const [family, ...details] = value.split(":");
  const localizedFamily = openingFamilies[family.trim()];
  if (!localizedFamily) return value;
  if (!details.length) return localizedFamily;
  const localizedDetails = details.join(":").split(",").map((part) => {
    const trimmed = part.trim();
    return openingVariations[trimmed] ?? trimmed;
  });
  return `${localizedFamily}: ${localizedDetails.join(", ")}`;
}
