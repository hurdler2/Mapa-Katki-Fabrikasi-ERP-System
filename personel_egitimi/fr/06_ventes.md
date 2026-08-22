# 06 — Module Ventes

**Public :** Représentants commerciaux, directeur des ventes, conseiller technique
**Durée :** 90 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Ventes :
1. Gestion des Clients
2. Commande de Vente (Sales Order)
3. BL Client — Bordereau de Livraison
4. Flux BL → Facture
5. Trial Batch (Batch d'Essai)
6. Mix Design Consultation
7. Applicator Training
8. Performance Warranty
9. Customer Site Test
10. Rapport BL-Facture

---

## 1. Gestion des Clients

### 1.1 Nouveau Client

**Chemin :** Admin → `/admin/masterdata/customer/add/`

1. **Code :** Ex. `C-2026-045`
2. **Nom :** Ex. `SARL Cimenterie Blida`
3. **Contact :** Téléphone, e-mail
4. **Adresse**
5. **E-mail**
6. **Escompte par défaut (%) :** Ex. `10.00` — appliqué automatiquement sur ses factures
7. **Actif :** True

### 1.2 Liste des Clients

**Chemin :** Admin → `/admin/masterdata/customer/`

- **list_editable :** Escompte modifiable directement dans la liste
- **Recherche :** code ou nom

### 1.3 Application Automatique de l'Escompte

À la nouvelle facture :
1. Sélectionner le client dans la dropdown
2. Si `default_discount_pct > 0` :
   - Le champ **« Taux d'escompte »** se remplit automatiquement
   - Message vert : `✓ Escompte défini : 15%`
3. Modifiable manuellement si besoin

---

## 2. Commande de Vente (Sales Order)

### 2.1 Nouvelle Commande

**Chemin :** Admin → `/admin/sales/salesorder/add/`

1. **N° Commande :** Ex. `SO-2026-0042`
2. **Client**
3. **Date commande**
4. **Date de livraison**
5. **Statut :** DRAFT
6. **Notes**

**Lignes :**
- Produit
- Quantité
- Unité
- Prix unitaire

### 2.2 Cycle de Vie de la Commande

```
DRAFT → CONFIRMED → PARTIAL → SHIPPED
                            ↘ CANCELLED
```

### 2.3 Mise à Jour Automatique du Statut

Après chaque expédition, `refresh_status()` :
- Aucun envoyé → CONFIRMED
- Partiel → PARTIAL
- Tout envoyé → SHIPPED

---

## 3. BL Client — Bordereau de Livraison

### 3.1 Qu'est-ce que le BL Client ?

Le Bordereau de Livraison (BL) est le document de sortie physique du produit livré. En Algérie, le BL est émis **avant** la facture ; la facture couvre un ou plusieurs BL par la suite.

### 3.2 Liste des BL Clients

**Chemin :** Menu gauche → **Ventes** → **BL Client**

URL directe : `/portal/satis/bl/`

**Cartes KPI :**
- Brouillons
- Livrés (prêts à facturer)
- Facturés
- Annulés

**Tableau :**
- Case à cocher (pour créer facture)
- N° BL, Client, Commande, Date livraison
- Chauffeur / Plaque
- **Badge statut :**
  - ⚫ Brouillon
  - 🟠 Livré
  - 🟢 Facturé
  - 🔴 Annulé
- Facture (lien si applicable)

**Filtres :** Tous / Brouillon / Livré / Facturé / Annulé

### 3.3 Nouveau BL Client

**Chemin :** Admin → `/admin/sales/shipment/add/`

1. **N° BL :** Ex. `BL-202608-042`
2. **Client**
3. **Commande** (optionnel)
4. **Date livraison**
5. **Détail expédition :**
   - Transporteur
   - Plaque véhicule
   - Nom chauffeur
   - Adresse livraison
6. **Statut :** DRAFT
7. **Notes**

**Lignes (Shipment Lines) :**
- Ligne SO
- Output Container (IBC) — d'un batch RELEASED
- Quantité

**Contrôles (BR) :**
- IBC seulement de batches **QC-RELEASED**
- Un IBC ne peut être expédié 2 fois
- Ligne SO fournie → produits doivent correspondre

### 3.4 Page Détail BL

Détail portal :
- Numéro BL + badge statut
- Client + commande
- **Carte détail expédition** (date, transporteur, plaque, chauffeur, adresse)
- **Tableau lignes (basé IBC) :**
  - Produit
  - Code IBC
  - Quantité
  - Prix unitaire
  - Montant (HT)
- **Total (HT)** en bas
- **Panneau Facturation :**
  - Facture existante : lien
  - Sinon : bouton **« 🧾 Créer Facture depuis ce BL »**

### 3.5 Cycle de Vie du BL

```
DRAFT → DELIVERED → INVOICED
              ↘ CANCELLED
```

---

## 4. Flux BL → Facture

### 4.1 Facture depuis un BL Unique

**Chemin :** Détail BL → bouton **« 🧾 Créer Facture depuis ce BL »**

Automatique :
1. Nouvelle `Invoice` (SALES)
2. `default_discount_pct` client → escompte facture
3. InvoiceLine par ligne BL (avec info IBC)
4. Numéro facture : `INV-BL-<timestamp>`
5. Échéance : date facture + 30 jours
6. BL passe à `INVOICED`
7. Facture en `DRAFT`

### 4.2 Facture depuis Plusieurs BL

**Chemin :** Liste BL → cocher plusieurs → **« 🧾 Créer Facture depuis BL sélectionnés »**

**Contraintes :**
- Tous les BL **du même client**
- Aucun INVOICED
- Aucun CANCELLED
- Au moins une ligne par BL

Toutes les lignes fusionnées dans une facture.

### 4.3 Escompte Automatique

Client avec `default_discount_pct = 10.00` :
- Facture `discount_pct = 10.00`
- Calcul :
  - `multiplier = 0.9`
  - `discount_amount = total_line_ht × 0.10`
  - `total_ht = total_line_ht - discount_amount`

BL détail affiche : `Escompte client (10,00%) appliqué automatiquement.`

---

## 5. Trial Batch (Batch d'Essai)

### 5.1 Qu'est-ce qu'un Trial Batch ?

Petit échantillon envoyé au client pour test terrain avant commande. Modèle Sika/BASF.

### 5.2 Nouveau Trial

**Chemin :** Admin → `/admin/sales/trialbatch/add/`

1. **N° Trial :** Ex. `TRL-2026-001`
2. **Client**
3. **Produit candidat**
4. **Date d'essai**
5. **Quantité échantillon :** Ex. `25 kg`
6. **Adresse du chantier**
7. **Marque ciment client :** Ex. `Ciments d'Algérie CEM I`
8. **Classe ciment :** Ex. `CEM I 42.5 R`
9. **Taille max granulat**
10. **Slump cible :** Ex. `S4 (160-210 mm)`
11. **Rapport E/C cible :** Ex. `0.450`
12. **Dose (%)**
13. **Responsable**

### 5.3 Résultats du Trial

- Slump initial
- Slump 30/60/90 min
- Température site
- Notes équipe terrain

### 5.4 Cycle de Vie

```
PLANNED → SHIPPED → IN_TRIAL → SUCCESS
                           ↘ FAILED
                           ↘ CANCELLED
```

---

## 6. Mix Design Consultation

### 6.1 Concept

Optimisation dosage pour projet spécifique client — climat chaud/froid, résistance précoce.

### 6.2 Nouvelle Consultation

**Chemin :** Admin → `/admin/sales/mixdesignconsultation/add/`

1. **N° Consultation :** Ex. `MDC-2026-001`
2. **Client**
3. **Date demande**
4. **Nom projet :** Ex. `Injection barrage - Béjaïa`
5. **Classe béton cible :** Ex. `C40/50`
6. **Exigences spéciales :** Climat chaud, eau de mer, résistance précoce
7. **Produits proposés**
8. **Dosage proposé**
9. **Consultant technique**
10. **Rapport de recommandation :** PDF
11. **Statut :** REQUESTED → IN_STUDY → DELIVERED → IMPLEMENTED

---

## 7. Applicator Training

### 7.1 Enregistrement Formation

Modèle Sika/Chryso — formation équipe terrain client.

**Chemin :** Admin → `/admin/sales/applicatortraining/add/`

1. **N° Formation :** Ex. `ATR-2026-001`
2. **Client**
3. **Date formation**
4. **Lieu**
5. **Sujets :** Ex. « Calibrage dosage, gestion slump, sécurité »
6. **Produits couverts**
7. **Nombre participants**
8. **Liste participants**
9. **Formateur**
10. **Durée (heures)**
11. **Attestation délivrée**
12. **Attestation groupée PDF**
13. **Score satisfaction (1-5)**

---

## 8. Performance Warranty

### 8.1 Concept

Garantie écrite produit+client+projet. Sika : 60+ pays, 10-25 ans.

### 8.2 Nouvelle Garantie

**Chemin :** Admin → `/admin/sales/performancewarranty/add/`

1. **N° Garantie**
2. **Client**
3. **Produit**
4. **Nom projet**
5. **Emplacement projet**
6. **Quantité livrée**
7. **Début + Fin garantie**
8. **Résumé couverture**
9. **Exclusions**
10. **Signataire**
11. **Date signature**
12. **Document garantie PDF**
13. **Statut :** ACTIVE / EXPIRED / CLAIMED / VOIDED

---

## 9. Customer Site Test

### 9.1 Concept

Mesures terrain 7/14/28 jours — résistance cube, slump, température.

### 9.2 Nouveau Site Test

**Chemin :** Admin → `/admin/quality/customersitetest/add/`

1. **N° Test**
2. **Ligne Facture liée** (optionnel)
3. **Batch**
4. **Nom projet**
5. **Emplacement site**
6. **Date test**
7. **Type test :**
   - SLUMP
   - CUBE_7 (Cube 7 jours)
   - CUBE_14
   - CUBE_28
   - TEMPERATURE
   - AIR_CONTENT
   - DURABILITY
   - OTHER
8. **Valeur mesurée**
9. **Unité** (MPa, mm, °C)
10. **Valeur cible**
11. **Verdict :** PASS / FAIL / MARGINAL / NA
12. **Testeur** (client/labo)
13. **Rapport labo PDF**

---

## 10. Rapport BL-Facture

### 10.1 Consultation Rapport

**Chemin :** Menu gauche → **Rapports** → **BL-Facture Matching**

URL directe : `/portal/rapor/bl-fatura/`

**4 Cartes KPI :**
- BL matchés
- BL en attente
- Montant en attente
- BL annulés

**Tableau BL non facturés (alerte jaune) :**
- N° BL, client, date, montant (HT), statut
- **Critique :** ces BL doivent être facturés rapidement (cash flow)

**Tableau BL matchés (50 derniers) :**
- N° BL, client, date, lien facture, date facture

---

## 11. FAQ

**Q : Escompte non appliqué automatiquement ?**
R : Le champ `default_discount_pct` est vide sur la fiche client. Le remplir + enregistrer.

**Q : Pas de formulaire portal pour BL ?**
R : Actuellement admin uniquement. Portal offre liste + détail + création facture.

**Q : Même IBC dans deux BL ?**
R : Non. `OutputContainer` OneToOne — après expédition, `shipment_reference` rempli, non réutilisable.

**Q : Fusionner BL de clients différents ?**
R : Non. Contrainte « même client » dans `create_invoice_from_bl()`.

**Q : Trial batch échoué ?**
R : Statut FAILED + notes. Ensuite Mix Design Consultation pour révision recette.

---

## 12. Exercices Pratiques

1. **Nouveau client :** Escompte 12%, actif
2. **Trial batch :** 25 kg, CEM I 42.5 R, slump S4 cible
3. **BL Client :** Nouveau BL (2 IBC), statut livré
4. **Créer facture :** Depuis le BL, escompte auto
5. **Site test :** Résistance cube 28 jours 42.5 MPa, PASS

Montrer au directeur ventes.
