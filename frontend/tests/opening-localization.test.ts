import assert from "node:assert/strict";
import test from "node:test";

import { localizeOpeningFamily, localizeOpeningName, localizeOpeningVariation } from "../src/lib/opening-localization.ts";

test("common opening families use established Russian names", () => {
  const cases = {
    "Sicilian Defense": "Сицилианская защита",
    "Caro-Kann Defense": "Защита Каро-Канн",
    "French Defense": "Французская защита",
    "Queen's Gambit": "Ферзевый гамбит",
    "King's Indian Defense": "Староиндийская защита",
    "English Opening": "Английское начало",
    "Queen's Pawn Game": "Дебют ферзевых пешек",
    "Grob Opening": "Дебют Гроба",
    "Slav Defense": "Славянская защита",
    "Zukertort Opening": "Дебют Цукерторта",
  };
  for (const [canonical, localized] of Object.entries(cases)) {
    assert.equal(localizeOpeningFamily(canonical), localized);
    assert.equal(localizeOpeningName(canonical), localized);
  }
});

test("known variations compose with a localized family", () => {
  assert.equal(localizeOpeningName("Caro-Kann Defense: Exchange Variation"), "Защита Каро-Канн: Разменный вариант");
  assert.equal(localizeOpeningName("Sicilian Defense: Najdorf Variation, English Attack"), "Сицилианская защита: Вариант Найдорфа, Английская атака");
  assert.equal(localizeOpeningVariation("Advance Variation"), "Вариант с выдвижением");
});

test("unknown canonical opening text is preserved", () => {
  assert.equal(localizeOpeningName("Unknown Invented Opening: Rare Line"), "Unknown Invented Opening: Rare Line");
  assert.equal(localizeOpeningFamily("Unknown Invented Opening"), "Unknown Invented Opening");
  assert.equal(localizeOpeningName(null), null);
});
