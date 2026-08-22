# 05 — Module Stock / Magasin

**Public :** Responsables magasin, agents réception, directeur magasin
**Durée :** 75 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Stock / Magasin :
1. Gestion Matières Premières et Lots
2. Réception (Goods Receipt)
3. Page Détail Stock (Alerte + Rupture)
4. Ajustement de Stock
5. Ajustement Multi-Lignes
6. Historique des Mouvements
7. Zones de Stockage
8. Échantillons de Rétention
9. Rapports

---

## 1. Gestion Matières Premières et Lots

### 1.1 Concept Matière Première

Une **matière première (RawMaterial)** est un composant utilisé dans les recettes de production. Exemples :
- `W` — Eau
- `M1` — Monomère A (PEG)
- `M2` — Monomère B (Acide acrylique)
- `IN` — Initiateur (Persulfate)
- `NaOH` — Base

Chaque MP a :
- **Code** et **Nom**
- **Type** (Eau, Retardateur, Superplastif., Composant, Autre)
- **Unité** (kg, L, tonne)
- **Densité** (kg/L pour liquides)
- **Durée de vie** (jours)
- **Seuil d'alerte**
- **Seuil de rupture**
- **Info REACH/SVHC** (si applicable)
- **Numéro CAS/EC**

### 1.2 Concept Lot

Un **lot (RawMaterialLot)** est un envoi spécifique d'une MP. Une même MP peut avoir plusieurs lots à différentes dates.

Chaque lot :
- **N° Lot** (unique — ex. `LOT-W-202606-014`)
- **Fournisseur**
- **Date réception**
- **Date de péremption**
- **Quantité reçue** et **Quantité restante**
- **Statut QC :** PENDING / RELEASED / QUARANTINE / REJECTED
- **Référence COA**
- **Coût unitaire** (DZD/kg)
- **Container/Cuve**

### 1.3 Consulter la Liste des Lots

**Chemin :** Menu gauche → **Stock / Magasin** → **Lots MP**

Alternatif : `/admin/inventory/rawmateriallot/`

Filtres :
- Statut QC
- Matière première
- Fournisseur
- Date réception

Badge coloré :
- 🟢 RELEASED — utilisable
- ⚫ PENDING — en attente de test
- 🟠 QUARANTINE — en quarantaine
- 🔴 REJECTED — refusé

---

## 2. Réception (Goods Receipt)

### 2.1 Nouvelle Réception

**Chemin :** Menu gauche → **Stock / Magasin** → **Nouvelle Réception**

URL directe : `/portal/stok/mal-kabul/`

1. **Fournisseur**
2. **Commande d'Achat (PO)** (optionnel)
3. **Matière Première**
4. **Quantité :** Ex. `1500` kg
5. **N° Lot :** Fourni par le fournisseur
6. **Date de péremption**
7. **Référence COA :** N° COA fournisseur
8. **Coût unitaire :** DZD/kg
9. **Container :** Cuve/emplacement (optionnel)
10. **Enregistrer**

Le système automatiquement :
- Crée un `RawMaterialLot`
- `qc_status = PENDING`
- `remaining_qty = received_qty`
- Écrit `StockMovement(RECEIPT)`

### 2.2 Libération d'un Lot (Approbation QC)

Après réception, QA teste le lot. Selon le résultat :

**Chemin :** Admin → détail RawMaterialLot → **Actions :**

- **Libérer le lot (RELEASED)** — Autorisation d'usage
- **Mettre en quarantaine** — Suspect, test supplémentaire
- **Refuser le lot** — Non utilisable

### 2.3 FEFO (First Expiry First Out)

Lors du dosage recette, le système utilise **FEFO** :
- Lot avec date de péremption la plus proche → consommé en premier
- Minimise le rebut
- **BR-QA-06 :** Consommation → lot décrémenté immédiatement

---

## 3. Page Détail Stock (Alerte + Rupture)

### 3.1 Consulter Détail MP

**Chemin :** Menu gauche → **Stock / Magasin** → cliquer sur une MP

URL directe : `/portal/stok/hammadde/<pk>/`

**En-tête :**
- Code + nom
- Type, unité, densité
- **Badge niveau (haut droite) :**
  - 🟢 **✓ Stock suffisant**
  - 🟠 **⚠ ALERTE**
  - 🔴 **🚨 RUPTURE**

**Carte Niveau de Stock :**
- Stock actuel (gros chiffre)
- Seuil d'alerte (jaune)
- Seuil de rupture (rouge)
- Valeur du stock (DZD)
- Progress bar coloré

**Lots Actifs :**
- Chaque lot RELEASED : n°, fournisseur, date, restant, coût unit.

**Historique des Mouvements (50 derniers) :**
- Date, Type (badge Consommation/Réception/Ajustement)
- Document Source (Ordre de Production, N° Ajustement)
- Quantité (+/− coloré)
- Prix unitaire (DZD)
- Observations
- Opérateur

### 3.2 Accès Rapides (Sidebar Gauche)

Sur la page détail :
- ➕ **Créer un ajustement**
- 📋 **Voir tous les mouvements**
- 📜 **Historique ajustements**

### 3.3 Réglage des Seuils

**Chemin :** Admin → RawMaterial → champs Alert threshold + Rupture threshold

Exemple :
- Alert threshold : `5000` kg
- Rupture threshold : `1000` kg

Résultat :
- Stock > 5000 kg → vert (OK)
- 1000 < Stock ≤ 5000 kg → jaune (ALERTE)
- Stock ≤ 1000 kg → rouge (RUPTURE — production peut s'arrêter)

---

## 4. Ajustement de Stock (Ligne Unique)

### 4.1 Qu'est-ce qu'un Ajustement ?

Documenter un écart d'inventaire, perte, dégât.

### 4.2 Nouvel Ajustement

**Chemin :** Menu gauche → **Stock / Magasin** → **Nouvel Ajustement**

URL directe : `/portal/stok/ajustement/yeni/`

1. **Lot (RELEASED) :** Depuis dropdown (quantité affichée)
2. **Type d'ajustement :**
   - `INVENTORY` — Inventaire
   - `LOSS` — Perte
   - `DAMAGE` — Dégât
   - `RETURN` — Retour fournisseur
   - `CORRECTION` — Correction
   - `OTHER` — Autre
3. **Nouvelle Quantité (Qté après)**
   - Auto : Delta = Qté après − Qté avant
4. **Motif :** Raison (texte libre — obligatoire)
5. **Document Justificatif (BR) :**
   - `LOSS`, `DAMAGE`, `RETURN` → **OBLIGATOIRE**
   - Autres → optionnel
   - Document type, référence, fichier

Le système :
- Crée `StockAdjustment`
- Crée `StockMovement (ADJUSTMENT)`
- Met à jour `RawMaterialLot.remaining_qty`

### 4.3 BR — Justificatif Obligatoire

**LOSS / DAMAGE / RETURN** sans document :

```
BR : document justificatif obligatoire pour Perte / Dégât / Retour.
```

---

## 5. Ajustement Multi-Lignes

### 5.1 Quand l'Utiliser ?

Inventaire mensuel — plusieurs lots ajustés **dans un même document**.

### 5.2 Nouvel Ajustement Multi-Lignes

**Chemin :** Menu gauche → **Stock / Magasin** → **Multi-Lignes**

URL directe : `/portal/stok/ajustement/multi/`

1. **Type d'ajustement**
2. **Motif général :** Ex. « Inventaire mensuel Août 2026 »
3. **Tableau 8 lignes :**

| # | Lot | Nouvelle Qté | Motif ligne |
|---|-----|--------------|-------------|
| 1 | W · LOT-W-014 · 3450 kg | 3400 | Manquant |
| 2 | G · LOT-G-023 · 5279 kg | 5300 | Surplus |

4. **Justificatif :** Document général
5. **Enregistrer** — atomique

Système crée :
- 1 `StockAdjustment` (résumé)
- N `StockAdjustmentLine` (chaque ligne)
- N `StockMovement`

---

## 6. Historique des Mouvements

### 6.1 Voir Tous les Mouvements

**Chemin :** Admin → `/admin/inventory/stockmovement/`

Filtres :
- Movement type
- Timestamp
- Lot

### 6.2 Filtre par MP

- Page détail MP → tableau **Historique** (50 derniers)
- Admin : filtre `lot__raw_material__id__exact=<pk>`

### 6.3 Mouvements Non Modifiables

**Important :** `StockMovement` **NE SE SUPPRIME PAS**. Mouvement erroné → écriture inverse. Intégrité audit trail.

---

## 7. Zones de Stockage

### 7.1 Zone de Stockage

Zones séparées par classe de danger :
- Zone-01 : Liquides inflammables (Classe 3)
- Zone-02 : Corrosifs (Classe 8)
- Zone-03 : Oxydants (Classe 5.1)

### 7.2 Compatibilité Stockage

**Chemin :** Admin → `/admin/chemicals/storageincompatibility/`

Ex : Classe 3 (inflammable) + Classe 5.1 (oxydant) incompatibles — risque explosion.

---

## 8. Échantillon de Rétention

### 8.1 Concept

Échantillon prélevé de chaque batch. Conservé durée de vie + 6 mois. Source de ré-analyse en cas de réclamation.

### 8.2 Enregistrement

**Chemin :** Admin → `/admin/chemicals/retentionsample/add/`

1. N° Échantillon
2. Batch lié
3. Lieu de stockage
4. Date prélèvement
5. Date de péremption
6. Statut : STORED / RETESTED / DISPOSED / LOST

---

## 9. Rapports

### 9.1 Tableau de Bord Magasin

**Chemin :** Menu gauche → **Tableau de bord Magasin**

Affiche :
- Répartition statuts lots
- Lots en attente de test
- Lots libérés (par date de péremption)
- Alarmes durée de vie

### 9.2 Valorisation Stocks

**Chemin :** Menu gauche → **Rapports** → **Valorisation Stocks**

- Par MP :
  - Quantité
  - Coût moyen pondéré
  - Valeur (DZD)
  - Badge niveau
- Valeur totale MP

---

## 10. FAQ

**Q : Réception faite mais lot pas RELEASED ?**
R : Test QC nécessaire. QA doit exécuter `Actions → Libérer`.

**Q : Comment fonctionne FEFO ?**
R : Système choisit le lot avec `expiry_date` le plus proche parmi les RELEASED.

**Q : Ajustement fait sans document pour LOSS ?**
R : Types LOSS / DAMAGE / RETURN → document obligatoire.

**Q : Ligne vide dans multi-lignes possible ?**
R : Oui, les lignes sans lot ou quantité sont ignorées.

**Q : Progress bar > 100% ?**
R : Oui — si stock > 2× alert threshold, la barre est pleine mais niveau OK.

---

## 11. Exercices Pratiques

1. **Nouvelle réception :** 2000 kg RM1, fournisseur BASF, COA, coût unit.
2. **Libération lot :** Libérer après test QC
3. **Ajustement :** Inventaire sur W lot : -50 kg
4. **Multi-lignes :** Inventaire mensuel — 3 lots dans un document
5. **Rapport :** Noter valeur totale MP du rapport Valorisation

Montrer au directeur magasin.
