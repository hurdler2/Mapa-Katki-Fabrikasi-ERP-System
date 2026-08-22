# 07 — Module Achats

**Public :** Responsables achats, directeur des achats, supply chain
**Durée :** 60 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Achats :
1. Gestion des Fournisseurs
2. Commande d'Achat (Purchase Order — PO)
3. Réception (Goods Receipt — GR)
4. Facture d'Achat (Purchase Invoice — AP)
5. Paiement
6. Suivi Portal et Rapports

---

## 1. Gestion des Fournisseurs

### 1.1 Nouveau Fournisseur

**Chemin :** Admin → `/admin/masterdata/supplier/add/`

1. **Code :** Ex. `S-2026-005`
2. **Nom :** Ex. `BASF Master Builders Solutions Algérie`
3. **Contact :** Téléphone, e-mail
4. **Adresse**
5. **NIF :** Numéro d'Identification Fiscale
6. **NIS :** Numéro d'Identification Statistique
7. **RC :** Registre de Commerce
8. **IBAN/RIB :** Coordonnées bancaires
9. **Conditions de paiement :** Ex. `Net 30`, `Net 60`
10. **Actif :** True

### 1.2 Liste des Fournisseurs

**Chemin :** Admin → `/admin/masterdata/supplier/`

- Code, nom, NIF
- Recherche : code, nom, NIF
- Filtre actif/inactif

### 1.3 Informations Légales Algériennes

Champs **obligatoires** pour un fournisseur en Algérie :
- **NIF (Numéro d'Identification Fiscale)**
- **NIS (Numéro d'Identification Statistique)**
- **RC (Registre de Commerce)**

Ces informations sont utilisées sur les factures et déclarations DGI.

---

## 2. Commande d'Achat (Purchase Order)

### 2.1 Nouvelle PO

**Chemin :** Admin → `/admin/purchasing/purchaseorder/add/`

1. **N° PO :** Ex. `PO-2026-042`
2. **Fournisseur**
3. **Date commande**
4. **Date d'échéance** (livraison prévue)
5. **Statut :** DRAFT
6. **Notes**

**Lignes :**
- Matière première
- Quantité
- Unité
- Prix unitaire (DZD)
- Date prévue

### 2.2 Cycle de Vie de la PO

```
DRAFT → APPROVED → PARTIAL_RECEIVED → RECEIVED
                                    ↘ CLOSED
```

- **DRAFT :** Brouillon
- **APPROVED :** Approuvée, envoyée au fournisseur
- **PARTIAL_RECEIVED :** Réception partielle
- **RECEIVED :** Réception complète
- **CLOSED :** Fermée (facture reçue + payée)
- **CANCELLED :** Annulée

### 2.3 PO PDF

*(Actuellement admin action — formulaire portal à venir)*

---

## 3. Réception (Goods Receipt — GR)

### 3.1 Réception Portal

**Chemin :** Menu gauche → **Stock / Magasin** → **Nouvelle Réception**

*Détaillé dans `05_stock.md` — résumé ici.*

1. **Fournisseur**
2. **Purchase Order** (lien optionnel)
3. **Matière Première**
4. **Quantité**
5. **N° Lot**
6. **Date de péremption**
7. **Référence COA**
8. **Coût unitaire**
9. **Container/Emplacement**
10. **Enregistrer**

Le système automatiquement :
- Nouveau `RawMaterialLot` (qc_status = PENDING)
- `StockMovement (RECEIPT)`
- Ligne PO `received_qty` mise à jour

### 3.2 Réception Partielle

PO 5000 kg, fournisseur envoie 3000 kg :
- Réception : `quantity=3000`
- Statut PO : `PARTIAL_RECEIVED`
- Restant : `2000 kg`

### 3.3 Réception Excédentaire

Fournisseur envoie 5500 kg (commande 5000 kg) :
- Pour les 500 kg supplémentaires :
  - Accepter → ouvrir NCR (Supplier root cause)
  - Refuser → retour
  - Décision après négociation → CAPA possible

---

## 4. Facture d'Achat (AP Invoice)

### 4.1 Nouvelle Facture d'Achat

**Chemin :** Menu gauche → **Comptabilité** → **Nouvelle Facture**

- **Type :** `Achat (AP)`
- **Fournisseur** (Client masqué)
- **N° Facture :** Numéro fourni par le fournisseur
- **Date facture + échéance**
- **Ligne facture** (Produit/MP, quantité, prix HT, TVA)
- **Pièce jointe :** PDF/JPG facture originale du fournisseur (obligatoire pour notification DGI)

### 4.2 Rapprochement 3 Voies (Three-Way Match)

Après saisie facture, contrôle trois données :
1. **PO** — quantité + prix commandés
2. **GR** — quantité réellement reçue
3. **Facture** — quantité + prix facturés

**Scénarios écart :**
- Facture > GR → contacter fournisseur
- Facture prix > PO → contacter fournisseur
- Quantité/prix concordent → approuver et payer

---

## 5. Paiement

### 5.1 Paiement Fournisseur

Détaillé dans `02_comptabilite.md`.

**Chemin :** Détail Purchase Invoice → **Nouveau Paiement**

1. **Direction :** `Décaissement (au fournisseur)`
2. **Méthode :** Virement (fréquent) / Chèque / Espèces
3. **Montant + date**
4. **Détails banque** (virement/chèque)

### 5.2 Paiement par Virement (Fréquent)

- Depuis banque algérienne via EFT
- Méthode `Virement / EFT`
- Banque de transfert : **BEA / BNA / CPA** etc.
- IBAN
- Date de transfert

### 5.3 Paiement par Chèque

- Méthode chèque → panneau spécifique
- N° chèque, date émission, date échéance
- Chèque post-daté fréquent : 60 jours
- Statut : `Émis` → payé banque : `Payé`

---

## 6. Suivi Portal et Rapports

### 6.1 Tableau de Bord Achats

**Chemin :** Menu gauche → **Tableau de bord Achats**

Affiche :
- PO en attente (DRAFT + APPROVED)
- Réceptions attendues (30 jours)
- Stocks critiques (rupture/alerte)
- Total achats du mois

### 6.2 Échéancier Fournisseurs

**Chemin :** Menu gauche → **Rapports** → **Échéancier Fournisseurs**

- Tranches : 0-30, 31-60, 61-90, 90+ jours
- Total dette ouverte
- Répartition par fournisseur

### 6.3 Compte Fournisseur

*(Fonctionnalité à venir — accessible via admin actuellement)*

### 6.4 Rendements Fournisseurs

*(À venir — délai livraison, qualité, ponctualité)*

---

## 7. FAQ

**Q : PO créée mais fournisseur envoie partiel, comment suivre le reste ?**
R : Statut PO auto `PARTIAL_RECEIVED`. `received_qty` par ligne montre l'écart commande vs. reçu.

**Q : Montant facture différent de la réception ?**
R : Informer la comptabilité. Écart < 2% tolérable. Sinon demander correction ou note de crédit.

**Q : Nouveau fournisseur sans NIF/NIS/RC, dois-je retarder l'enregistrement ?**
R : Oui — obligatoire pour DGI Algérie. Demander les documents légaux avant toute facturation.

**Q : Chèque post-daté refusé par la banque, que faire ?**
R : Payment → check_status = `BOUNCED`, check_bounce_reason. Facture revient à `PARTIALLY_PAID`. Contacter le fournisseur.

**Q : PO à annuler mais fournisseur refuse ?**
R : Selon conditions contractuelles. Demander annulation ; si accepté PO → `CANCELLED`. Sinon la commande reste valide.

**Q : Plusieurs MP du même fournisseur dans une PO ?**
R : Oui. PO multi-lignes supportées.

**Q : Fournisseur donne escompte early payment ?**
R : Champ `discount_pct` sur la facture (comme côté ventes). Montant escompte dans l'enregistrement paiement.

---

## 8. Exercices Pratiques

1. **Nouveau fournisseur :** NIF/NIS/RC complets, RIB
2. **Créer PO :** 3 MP, quantités différentes
3. **Réception :** Partielle sur 2 lignes de la PO
4. **Facture d'achat :** Facture du reçu + pièce jointe fournisseur
5. **Paiement :** Virement BEA

Montrer au directeur des achats.
