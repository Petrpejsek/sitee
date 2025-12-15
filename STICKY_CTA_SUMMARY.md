# Sticky CTA — Quick Summary

## ✅ Co bylo přidáno

**High-conversion zelený CTA button**, který scrolluje na hlavní sales sekci (Section 06).

---

## 📍 Umístění

### Desktop
- **Header (vpravo)** — vedle "Update report" buttonu
- **Sticky** — vždy viditelný při scrollu

### Mobile
- **Bottom bar** — fixní spodní lišta
- **Sticky** — vždy viditelný při scrollu
- **Full-width** — celá šířka obrazovky

---

## 💬 Text CTA (dynamický)

### Všude mimo Section 06:
```
"Become a Customer Magnet in AI"
```

### V Section 06 (sales sekci):
```
"See What We'll Build"
```

**Proč se mění:**
- Mimo sekci → magnet framing (benefit)
- V sekci → konkrétní deliverables

---

## 🎯 Cíl scrollu

**Anchor:**
- **Section ID:** `section_6`
- **Název:** "06. THE SOLUTION"
- **Obsah:** Complete AI-Ready Website (4-part sales block)

---

## 🎨 Design

### Barva
- **Background:** Emerald green (`#059669`)
- **Text:** Bílá, tučná
- **Hover:** Tmavší emerald (`#047857`)

### Styl
- ✅ Prémiový vzhled
- ✅ Klidný (ne agresivní)
- ✅ Jasný kontrast s headerem
- ✅ Smooth transition on hover

---

## 🔧 Funkce

```jsx
// Desktop (header)
<button onClick={() => scrollTo('section_6')}>
  {activeSection === 'section_6' 
    ? 'See What We'll Build' 
    : 'Become a Customer Magnet in AI'}
</button>

// Mobile (bottom)
<button onClick={() => scrollTo('section_6')}>
  {activeSection === 'section_6' 
    ? 'See What We'll Build' 
    : 'Become a Customer Magnet in AI'}
</button>
```

---

## ✅ Implementováno

- [x] Header CTA (desktop, sticky)
- [x] Mobile CTA (bottom, sticky)
- [x] Smooth scroll na Section 06
- [x] Dynamický text (mění se v Section 06)
- [x] Zelená barva (emerald)
- [x] Premium styl
- [x] Responsive behavior

---

## 🚀 Test

### Desktop
1. Otevři stránku auditu
2. **CTA v headeru vpravo** (zelený)
3. Klikni → smooth scroll na Section 06
4. Text se změní na "See What We'll Build"

### Mobile
1. Otevři na mobilu
2. **CTA dole (sticky bar)**
3. Klikni → smooth scroll na Section 06
4. Text se změní na "See What We'll Build"

---

## 📂 Soubory změněny

- ✅ `frontend/src/pages/ReportPage.jsx`
  - Header CTA přidán (řádky 383-398)
  - Mobile CTA aktualizován (řádky 2106-2114)
  - Navigace aktualizována (05 Cost, 06 Solution)

---

## 💡 Proč to funguje

### User Journey
1. **Sections 01-05:** Problem, barriers, cost
2. **CTA visible:** "Become a Customer Magnet in AI"
3. **Click CTA:** Smooth scroll to solution
4. **Section 06:** Full sales block with packages
5. **Decision:** Choose package tier

### Copy Strategy
- **"Become a Customer Magnet in AI"**
  - Benefit-driven (outcome, not feature)
  - Matches hero headline from Section 06
  - AI positioning (relevant to audit)
  - Action verb (active voice)

---

**Status: ✅ HOTOVO**

CTA vede přesně na **Section 06 — Complete AI-Ready Website** (hlavní sales blok).
