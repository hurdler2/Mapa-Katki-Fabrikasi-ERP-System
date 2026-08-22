# 04 — Module Qualité / QA

**Public :** Responsables qualité (QA), techniciens laboratoire, directeur qualité
**Durée :** 90 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Qualité :
1. Catalogue Qualité (Paramètres QC + méthodes EN 480)
2. Spécifications Qualité
3. Flux d'approbation QA et versioning
4. Contrôle Per-Gate (Gate A/B/C)
5. Plans d'échantillonnage (BR-QA-12)
6. Prélèvement et Saisie de Résultats (BR-QA-04)
7. Gestion des Non-Conformités (NCR + BR-QA-11)
8. COA (Certificate of Analysis)
9. CAPA (Action Corrective)
10. Suivi Portal et Rapports

---

## 1. Catalogue Qualité (Paramètres QC)

### 1.1 Qu'est-ce qu'un Paramètre QC ?

Un paramètre QC est une propriété mesurable utilisée dans les spécifications qualité. Exemples :
- **pH** (unité : aucune, précision : 1)
- **DENSITY** (unité : g/cm³, précision : 3)
- **SOLIDS** (matière sèche %) (unité : %, précision : 2)
- **CHLORIDE** (unité : %, précision : 3)
- **VISCOSITY** (unité : mPa·s, précision : 2)

### 1.2 Consulter le Catalogue

**Chemin :** Menu gauche → **Qualité** → **Catalogue Propriétés / Tests**

URL directe : `/portal/kalite/katalog/`

Tableau affiche :
- **Code** (ex. `PH`)
- **Nom de la propriété**
- **Unité** (ex. `g/cm³`)
- **Méthode** (ex. `EN 480-8 (Matière sèche %)`, `EN ISO 758 (Densité)`)
- **Précision décimales**

### 1.3 Ajouter un Nouveau Paramètre

**Chemin :** Admin → `/admin/quality/qcparameter/add/`

1. **Code :** Unique — ex. `TEMP`
2. **Nom :** Ex. `Température`
3. **Unité :** `°C`
4. **Méthode :** Sélectionner (EN 934-2, EN 480-1, EN 480-8, EN 480-10, ISO 758, Méthode interne)
5. **Référence méthode EN 480** (optionnel) : ex. `EN 480-8 § 5.2`
6. **Précision décimales :** 2 (défaut)
7. **Actif :** True
8. **Enregistrer**

---

## 2. Spécifications Qualité

### 2.1 Qu'est-ce qu'une Spécification ?

Une spécification qualité définit les limites acceptables d'un paramètre pour un **produit** ou une **matière première**.

Ex : `ADX-100 · pH · min : 4.5, max : 7.0, target : 6.0 · contrôlé au Gate C · CRITIQUE BR-QA-05`

### 2.2 Liste des Spécifications

**Chemin :** Menu gauche → **Qualité** → **Spécifications**

URL directe : `/portal/kalite/sartname/`

Tableau affiche :
- **Cible** (Produit ou Matière première)
- **Propriété**
- **v** (version)
- **Min / Max**
- **Gates** (A/B/C badges)
- **Critique** (badge BR-QA-05)
- **État** (Actif / Inactif)
- **Approbation QA**

**Filtre :** « Actif seulement » ou « Tous »

### 2.3 Nouvelle Spécification

**Chemin :** Admin → `/admin/quality/qcspec/add/`

1. **Paramètre :** Depuis le catalogue (ex. PH)
2. **Produit** OU **Matière première** — un seul (XOR)
3. **Valeurs :**
   - Min : `4.5`
   - Max : `7.0`
   - Target : `6.0`
   - Tolérance (%) : `5.0`
4. **is_mandatory :** True (mesure obligatoire ?)
5. **is_critical (BR-QA-05) :** True → l'écart déclenche NCR critique
6. **Contrôle Per-Gate :**
   - `check_at_gate_a` : contrôle Gate A (réception)
   - `check_at_gate_b` : contrôle Gate B (in-process)
   - `check_at_gate_c` : contrôle Gate C (produit fini)
7. **Versionnage :**
   - **Version :** 1, 2, 3, ...
   - **Date d'effet**
   - **is_active :** True (une seule active par cible)
8. **Approbation QA :**
   - **Créé par** (auto : votre utilisateur)
   - **Approuvé par (QA) :** Responsable QA
   - **Date d'approbation**

**Important :** Pour mettre `is_active=True`, le champ `approved_by` doit être **rempli**. Sinon erreur.

---

## 3. Flux d'Approbation QA et Versioning

### 3.1 Pourquoi le Versioning ?

Les spécifications évoluent avec le temps :
- Retours client → tolérance resserrée
- Nouvelle exigence légale → limite stricte
- Formule produit modifiée → paramètre change

Chaque changement est une nouvelle **version**. Les anciennes sont conservées (audit trail).

### 3.2 Changer de Version

Pour passer de `ADX-100 pH v1` (min 4.5, max 7.0) à **v2** (min 4.8, max 6.8) :

1. **Créer nouvelle QCSpec :** même produit+paramètre, `version=2`, nouvelles limites
2. Éditer v1 : `is_active=False`
3. Enregistrer v2 avec `is_active=True` (avec approbation QA)

Le système contrôle automatiquement — une seule version active par produit+paramètre.

### 3.3 Page Détail Spécification

Lorsque vous cliquez sur une spécification :
- **Carte valeurs limites** (Min / Cible / Max / Tolérance)
- Alerte BR-QA-05 si critique
- **Contrôles Gate** (trois cartes colorées A/B/C)
- Panneau **Version + Approbation QA**
- Liste des **autres versions**

---

## 4. Contrôle Per-Gate (Gate A / B / C)

Dans la méthodologie MCOS, la production passe par trois Gates :

- **Gate A** — Réception (qualité entrée MP)
- **Gate B** — In-Process (contrôle en cours)
- **Gate C** — Produit Fini (QC final)

### 4.1 Comment Définir les Gates ?

À la création de la spécification, cocher pour chaque paramètre quels Gates contrôlent. Exemples :

| Paramètre | Gate A | Gate B | Gate C |
|-----------|--------|--------|--------|
| pH | ⬜ | ✅ | ✅ |
| Density | ⬜ | ⬜ | ✅ |
| Solids | ⬜ | ⬜ | ✅ |
| Chloride | ⬜ | ⬜ | ✅ (Critique BR-QA-05) |
| Viscosity | ⬜ | ✅ | ✅ |

**Pattern typique :**
- Propriétés physico-chimiques (Density, Solids) → Gate C seulement
- Paramètres critiques (Chloride) → Gate C + critique
- Contrôle réaction (pH, T) → Gate B + Gate C

---

## 5. Plans d'Échantillonnage (BR-QA-12)

### 5.1 Qu'est-ce qu'un Plan d'Échantillonnage ?

Un plan d'échantillonnage définit **à quel Gate**, **avec quel déclencheur**, **avec quelle fréquence** les échantillons sont prélevés.

### 5.2 Liste des Plans

**Chemin :** Menu gauche → **Qualité** → **Plans d'échantillonnage**

URL directe : `/portal/kalite/orneklem-plani/`

Tableau affiche :
- Code du plan
- Cible (Produit ou MP)
- Gate (badge coloré)
- Déclencheur
- Fréquence (1/N)
- Règle de taille d'échantillon
- État (Actif / Inactif)

### 5.3 Nouveau Plan

**Chemin :** Admin → `/admin/quality/samplingplan/add/`

1. **Code :** Ex. `SP-PF-001`
2. **Nom :** Ex. `Produit fini · pH + densité par batch`
3. **Domaine d'application :** Produit OU MP
4. **Gate :** A / B / C
5. **Déclencheur :**
   - `À la réception`
   - `Par ligne de BL`
   - `Après mélange`
   - `Par batch de production`
   - `À l'expédition`
   - `Programmé (calendrier)`
6. **Fréquence :** 1 = chaque batch, 5 = 1 sur 5
7. **Règle de taille :** Texte libre (ex. `sqrt(N)+1`, `3 fixes`, `MIL-STD-105E S-2`)
8. **is_active :** True

### 5.4 BR-QA-12 — Motif de Désactivation

Pour désactiver un plan :
- `is_active` = False
- `deactivation_reason` **obligatoire** — la raison doit être écrite

Le système applique cette règle (`clean()` validation).

**Exemple de motif :** *« Nouvelle méthode adoptée, plan SP-PF-002 mis en place, ancien plan devenu obsolète. »*

---

## 6. Prélèvement et Saisie de Résultats (BR-QA-04)

### 6.1 Qu'est-ce qu'un Échantillon ?

L'échantillon physique prélevé d'un batch ou lot. Des tests paramétriques sont effectués → résultats enregistrés comme `QCTestResult`.

### 6.2 BR-QA-04 — Verrouillage Spec

Au moment du prélèvement, la **version de QCSpec active est verrouillée** avec l'échantillon (`spec_locked`).

Même si la spec change ensuite, cet échantillon est évalué avec l'ancienne spec. **Critique** — lors d'un audit, réponse claire à « avec quelle spec ce test est passé/échoué ».

### 6.3 Nouveau Résultat de Test

**Chemin :** Admin → `/admin/quality/qctestresult/add/`

1. **Paramètre :** Depuis catalogue
2. **Lot** OU **Batch** — un seul
3. **spec_locked :** QCSpec active auto-sélectionnée (BR-QA-04)
4. **Gate :** A / B / C
5. **Valeur :** Résultat mesuré (arrondi selon précision)
6. **Verdict :** Auto-calculé selon la spec :
   - PASS (dans min-max)
   - FAIL (hors limites)
   - NA
7. **Testeur :** Nom du technicien
8. **Notes**

---

## 7. Gestion des Non-Conformités (NCR)

### 7.1 Qu'est-ce qu'un NCR ?

Un NCR (Non-Conformance Report) documente une non-conformité produit/procédé/système. Sources :
- Test qualité (résultat FAIL)
- Production (dépassement tolérance)
- Audit interne
- Fournisseur (MP non conforme)
- Réclamation client
- Maintenance
- HSE

### 7.2 Ouvrir un NCR

**Chemin :** Menu gauche → **QMS** → **Non-Conformités (NCR)** → **+ Nouveau NCR**

Alternatif : `/admin/qms/nonconformance/add/`

1. **N° NCR :** Ex. `NCR-2026-0042`
2. **Source :** QC_TEST, PRODUCTION, INTERNAL_AUDIT, SUPPLIER, CUSTOMER_COMPLAINT, MAINTENANCE, EHS, OTHER
3. **Sévérité :** LOW / MEDIUM / HIGH / CRITICAL
4. **Date détection**
5. **Détecté par :** Votre utilisateur (auto)
6. **Titre**
7. **Description**
8. **Cible (Generic FK)** : batch, lot, ordre, etc.
9. **Quantité affectée :** Ex. `500 kg`
10. **Gate :** A / B / C
11. **Root cause category (7 choix + Autre) :**
    - Qualité fournisseur
    - Équipement
    - Process / Opérateur
    - Conception formule
    - Erreur de mesure / échantillonnage
    - Environnemental
    - Autre
12. **Disposition :** PENDING → USE_AS_IS / REWORK / **REJECT** / **RETURN_TO_SUPPLIER** / DOWNGRADE / **WAIVER**
13. **Justificatif (BR-QA-11) :** PDF/JPG

### 7.3 BR-QA-11 — Justificatif Obligatoire

**Disposition = REJECT, RETURN_TO_SUPPLIER ou WAIVER** → `proof_document` **OBLIGATOIRE**.

- Le système contrôle avec `clean()`
- Si vide : `« BR-QA-11 : un document justificatif est requis pour Retour fournisseur / Rebut / Dérogation. »`

Documents typiques :
- REJECT : PV de destruction
- RETURN_TO_SUPPLIER : Lettre de notification + réponse fournisseur
- WAIVER : Note d'approbation du directeur qualité

### 7.4 Cycle de Vie du NCR

```
OPEN → INVESTIGATING → DISPOSITIONED → CLOSED
                                     ↘ CANCELLED
```

---

## 8. COA (Certificate of Analysis)

### 8.1 Qu'est-ce qu'un COA ?

Un COA est le résumé qualité d'un batch de production. Accompagne chaque produit livré au client.

### 8.2 Générer un COA Automatiquement

**Chemin :** Admin → ProductionBatch → sélectionner → **Action** → **Générer et publier COA**

1. Batch sélectionné
2. Système lit les `QCTestResult`
3. Tous PASS → COA en état `ISSUED`
4. Un FAIL → COA non généré (batch non RELEASED)

Contenu du COA :
- N° COA
- N° Batch + produit + version recette
- Date production
- Liste des paramètres + valeurs + verdicts + méthodes
- Signature + date

---

## 9. CAPA (Corrective and Preventive Action)

### 9.1 Qu'est-ce qu'un CAPA ?

Une action corrective (éliminer la cause) ou préventive (éviter réapparition) suite à une non-conformité.

### 9.2 Nouveau CAPA

**Chemin :** Menu gauche → **QMS** → **CAPA**

1. **N° CAPA**
2. **NCR lié** (si applicable)
3. **Type :** CORRECTIVE / PREVENTIVE
4. **Description**
5. **Analyse cause racine** (5 Why, Fishbone)
6. **Plan d'action**
7. **Responsable**
8. **Date limite**
9. **Vérification d'efficacité**

---

## 10. Suivi Portal et Rapports

### 10.1 Tableau de Bord Qualité

**Chemin :** Menu gauche → **Tableau de bord Qualité**

- Tests de lot en attente
- Tests de batch en attente (QC_HOLD)
- 30 derniers jours : total tests / PASS / FAIL
- Taux FAIL (rouge > 5% dangereux)

### 10.2 Suivi Conformité Spécifications

**Chemin :** Menu gauche → **Qualité** → **Spécifications** → filtre **actif**

D'un coup d'œil :
- Combien de spécifications actives
- Combien approuvées QA (vert ✓)
- Combien en attente d'approbation (rouge ⚠)

---

## 11. FAQ

**Q : J'essaie d'activer une spécification mais erreur ?**
R : Champ `approved_by` vide. Sélectionnez le responsable QA, `approved_at` se remplit auto, puis enregistrer.

**Q : Deux spécifications actives pour le même produit+paramètre possible ?**
R : Non. `UniqueConstraint` bloque. Désactiver l'ancienne avant d'activer la nouvelle.

**Q : Échantillon pris mais spec_locked pas rempli ?**
R : Pas de QCSpec active pour ce produit. Créez et activez la spécification d'abord.

**Q : NCR créé mais demande proof_document ?**
R : Disposition REJECT / RETURN_TO_SUPPLIER / WAIVER. Chargez le document ou changez la disposition.

**Q : Plan d'échantillonnage à désactiver demande motif ?**
R : BR-QA-12 obligatoire. Écrivez la raison précise dans `deactivation_reason`.

**Q : Je dois tester à Gate A mais ma spec n'a que Gate C ?**
R : Éditez la spécification, cochez `check_at_gate_a=True`. Alternative : créer une nouvelle version.

**Q : Un test FAIL affecte-t-il le batch ?**
R : Batch passe automatiquement en `QC_HOLD`. QA décide RELEASED (waiver) ou REJECTED. Un NCR peut être ouvert.

---

## 12. Exercices Pratiques

1. **Nouveau paramètre QC :** `VISCOSITY`, unité `mPa·s`, méthode EN 480-4, précision 2
2. **Spécification :** `ADX-100 · pH v2` (min 5.0, max 6.5, critique, Gate C, QA approuvée)
3. **Plan d'échantillonnage :** `SP-PF-002` — 1 échantillon par batch PF, Gate C
4. **Résultat test :** Pour un batch pH=5.8 → PASS auto-calculé
5. **NCR :** Pour un lot fournisseur CHLORIDE FAIL, disposition Return to supplier + justificatif

Une fois terminés, montrez au directeur qualité.
